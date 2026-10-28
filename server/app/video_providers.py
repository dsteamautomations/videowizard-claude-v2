"""Documented REST adapters. Submission is never retried by this module."""
import base64
import http.client
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import urlsplit
import httpx
from .config import settings
from .errors import Problem

GOOGLE='https://generativelanguage.googleapis.com/v1beta/interactions'
HF='https://api.higgsfield.ai'
MAX_VIDEO=200*1024*1024


def motion_text(snapshot):
    """design/84: the library's Omni house shape (fact sheet B1, B2, B7, B9): the frame tags first, the motion brief, the continuity line,
    one unbroken shot (Omni cuts to several shots by default), no dialogue or music, the pictures' roles in plain words, the length last."""
    two=bool(snapshot.get('end_image'))
    prompt='[# Sources <FIRST_FRAME>@Image1'+(' <LAST_FRAME>@Image2' if two else '')+']\n'
    prompt+=snapshot['motion_prompt']
    if (snapshot.get('ambient') or '').strip() and not re.match(r'\s*still\b',snapshot['ambient'],re.I):prompt+='\nThroughout the shot the surroundings stay alive: '+snapshot['ambient'].strip().rstrip('.')+'.'   # design/101 M3; a `still:` line asks for nothing
    prompt+='\nNatural, unhurried motion; no sudden, exaggerated or floating movement.'   # design/102 B3: how things move, not how much
    prompt+='\nSubject reconciliation:\n'+json.dumps(snapshot['subject_reconciliation'],ensure_ascii=False)
    prompt+='\nContinuity: '+(snapshot.get('continuity_notes') or '')
    for l in snapshot.get('person_lines') or []:prompt+='\n'+l   # design/111 F16: the fixed layer and the scene's colours
    if 'camera_move' in snapshot:prompt+='\nCamera: '+((snapshot['camera_move'] or '').strip().rstrip('.')+'; nothing else about the frame changes' if (snapshot['camera_move'] or '').strip() else 'locked off on a tripod; the frame does not move, drift, zoom or slide')+'.'   # design/112 S4
    for l in (snapshot.get('gaze_lines') or [])+(snapshot.get('heading_lines') or [])+(snapshot.get('tool_lines') or [])+([snapshot['fixed_line']] if snapshot.get('fixed_line') else []):prompt+='\n'+l   # design/110 F5, F6; design/111 F7, F8
    if (snapshot.get('light') or '').strip():prompt+='\nThe light does not change: '+snapshot['light'].strip().rstrip('.')+'.'   # design/103 A1
    prompt+='\nIn a single unbroken scene, one continuous shot, no scene cuts, no jump cuts. No dialogue. No music. No captions or overlay text.'
    prompt+='\nUse Image1 as the starting frame'+(' and Image2 as the final frame; the transition follows the action above' if two else '')+'. Preserve the depicted identities.'
    return prompt+f'\n{snapshot["duration_seconds"]}s'


def configured(provider):
    if provider not in ('google','higgsfield'):raise ValueError('Unknown video provider.')
    from . import keys as _keys
    idx,key=(next(iter(_keys.each('gemini',settings())),(None,'')) if provider=='google' else (None,settings().HF_API_KEY.get_secret_value().strip()))   # design/114: the next key of the pool
    key=key.strip()
    configured.last_index=idx
    if not key or any(ord(c)<33 or ord(c)>126 for c in key):
        raise Problem(503,'VIDEO_CONFIGURATION','Configure the selected provider key on the backend/worker. No automatic provider fallback.')
    return key


def transfer(url,method='GET',data=None,headers=None,limit=MAX_VIDEO):
    """HTTPS storage transfer pinned to a validated public IP, with no redirects or API key."""
    target=urlsplit(url)
    if target.scheme!='https' or not target.hostname or target.username or target.password or target.port not in (None,443):
        raise ValueError('Invalid provider storage URL.')
    addresses=socket.getaddrinfo(target.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Provider storage must resolve to a public address.')
    address=addresses[0][4][0]
    connection=http.client.HTTPSConnection(target.hostname,timeout=60,context=ssl.create_default_context())
    connection.sock=connection._context.wrap_socket(socket.create_connection((address,443),timeout=60),server_hostname=target.hostname)
    try:
        connection.request(method,target.path+('?' + target.query if target.query else ''),body=data,headers=headers or {})
        response=connection.getresponse()
        if not 200<=response.status<300:raise ValueError('Provider storage transfer failed; recover the same output.')
        raw=response.read(limit+1)
        if len(raw)>limit:raise ValueError('Provider output exceeds the storage limit.')
        return raw
    finally:connection.close()


class Provider:
    def __init__(self,name):self.name=name;self.key=configured(name);self.key_index=getattr(configured,'last_index',None)

    def request(self,method,url,body=None,identity=None,paid=False):
        headers={'x-goog-api-key':self.key,'Api-Revision':'2026-05-20'} if self.name=='google' else {'Authorization':'Key '+self.key}
        if identity and self.name=='higgsfield':headers['Idempotency-Key']=identity
        try:
            with httpx.stream(method,url,json=body,headers=headers,timeout=60,follow_redirects=False) as response:
                if not response.is_success:
                    if self.name=='google' and self.key_index is not None and response.status_code in (429,401,403):   # design/114: the key cools; the next attempt takes another
                        from . import keys as _keys;_keys.cool('gemini',self.key_index,_keys.reason_of(response.status_code))
                    code='VIDEO_REJECTED' if paid and 400<=response.status_code<500 and response.status_code not in (408,429) else 'VIDEO_UNKNOWN' if paid else 'VIDEO_PROVIDER'
                    raise Problem(502,code,'Provider request was not accepted or could not be confirmed. Review this saved attempt; no automatic resubmission.')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw)>MAX_VIDEO*4//3+4*1024*1024:raise ValueError('Provider response exceeds the bounded size.')
                return json.loads(raw) if raw else {}
        except (httpx.RequestError,ValueError):
            raise Problem(502,'VIDEO_UNKNOWN' if paid else 'VIDEO_PROVIDER','Provider response was interrupted or invalid. Recover this attempt without regenerating.') from None

    def build(self,snapshot,store):
        images=[snapshot[k] for k in ('start_image','end_image') if snapshot.get(k)]
        prompt=snapshot.get('effective_prompt') or motion_text(snapshot)
        if self.name=='google':
            return {'model':snapshot['model'],'background':True,'store':True,
                'input':[{'type':'image','mime_type':i['mime_type'],'data':base64.b64encode(store.get(i['key'])).decode()} for i in images]+[{'type':'text','text':prompt}],
                'response_format':{'type':'video','aspect_ratio':snapshot['aspect_ratio'],'resolution':snapshot['resolution']}}
        urls=[]
        for image in images:
            lease=self.request('POST',HF+'/files/generate-upload-url',{'content_type':image['mime_type']})
            transfer(lease['upload_url'],'PUT',store.get(image['key']),lease['upload_headers'],limit=1024*1024)
            # Public URL is sent only to the known provider; it is not fetched here.
            parsed=urlsplit(lease['public_url'])
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Invalid input URL.')
            urls.append(lease['public_url'])
        body={'image_url':urls[0],'prompt':prompt,'duration':snapshot['duration_seconds']}
        if snapshot['model']=='kling-video/v3.0/std/image-to-video':
            body.update(sound='off',multi_shots=False)
            if len(urls)==2:body['last_image_url']=urls[1]
        elif snapshot['model']=='bytedance/seedance-2.5/image-to-video':
            body.update(resolution=snapshot['resolution'],output_format='mp4',generate_audio=False)
            if len(urls)==2:body['end_image_url']=urls[1]
        else:raise ValueError('Unsupported Higgsfield model.')
        return body

    def submit(self,body,identity):
        # Higgsfield model is set from the frozen snapshot by the worker.
        return self.request('POST',GOOGLE if self.name=='google' else HF+'/'+self.model,body,identity,paid=True)

    def identity(self,result):
        value=result['id' if self.name=='google' else 'request_id']
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,2048}',value):raise ValueError('Invalid provider identity.')
        return value

    def poll(self,identity):
        self.identity({'id':identity,'request_id':identity})
        return self.request('GET',GOOGLE+'/'+identity if self.name=='google' else HF+'/requests/'+identity+'/status')

    def cancel(self,identity):
        self.identity({'id':identity,'request_id':identity})
        return self.request('POST',GOOGLE+'/'+identity+'/cancel' if self.name=='google' else HF+'/requests/'+identity+'/cancel')

    def state(self,result):
        state=result.get('status')
        if state in ('completed','failed','nsfw','canceled','cancelled'):return state
        if state in ('in_progress','queued','pending','processing'):return 'in_progress'
        raise ValueError('Unrecognized provider status; inspect the retained receipt.')

    def output(self,result):
        if self.name=='higgsfield':return transfer(result['video']['url'])
        videos=[c for s in result.get('steps',[]) if s.get('type')=='model_output' for c in s.get('content',[]) if c.get('type')=='video']
        if len(videos)!=1 or videos[0].get('mime_type')!='video/mp4':raise ValueError('Expected one MP4 video output.')
        # GET interactions currently returns inline content, including URI-mode creations.
        raw=base64.b64decode(videos[0]['data'],validate=True)
        if not raw or len(raw)>MAX_VIDEO:raise ValueError('Empty or oversized video output.')
        return raw
