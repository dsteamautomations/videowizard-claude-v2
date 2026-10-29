# Compliance checklist

Status: first draft, 2026-10-19, from DIRECTION.md section 5d. Run before generation and again before delivery. A second person signs it. Every regulatory reference below is to be verified against the current text of the rule; `verify_by` dates are set at the first real use and reviewed quarterly.

Each line has an id. The answer form's `compliance_flags` field carries the ids that apply to a job. The feedback record stores which ids passed.

## Before generation

| Id | Check | Applies when | Rule referenced | verify_by |
| --- | --- | --- | --- | --- |
| C01 `claims-sourced` | Every factual claim in the copy has a written source from the client. | any copy | ASCI code, honesty | |
| C02 `no-superlatives` | No unsubstantiated superlatives: "best", "No. 1", "guaranteed", "100 percent". | any copy | ASCI code, comparative claims | |
| C03 `mandatory-text-present` | The sector's mandatory text is in the copy list. Real estate: the project's RERA registration number. Food: the FSSAI licence number where required. Finance: the risk disclaimer. | industry set | RERA 2016; FSS Act 2006; SEBI advertisement code | |
| C04 `no-health-outcome-claims` | No cure, treatment or outcome claim. No before-and-after for conditions under the Drugs and Magic Remedies Act. Practitioner consent for any likeness. | healthcare | Drugs and Magic Remedies (Objectionable Advertisements) Act 1954; Drugs and Cosmetics Act | |
| C05 `no-education-guarantees` | No guaranteed placement, marks or ranks. | education | ASCI education guidelines | |
| C06 `no-return-promises` | No promised returns; risk disclaimer present. | finance | SEBI, RBI advertisement rules | |
| C07 `no-alcohol-tobacco` | Not produced. | any | Cable TV Rules; COTPA | |
| C08 `no-third-party-marks` | No third-party logos, competitor product shapes, franchise characters or recognisable protected designs; shelf templates have their real brands replaced. | any | trademark and copyright | |
| C09 `consent-on-file` | No real person unless client staff with a written consent record id. No public figures or lookalikes. No children's faces without parental consent and client policy. | any picture tagged person, or any generated person | client policy; IT Rules; platform rules | |
| C10 `festival-motif-check` | No deities on products, footwear, food or packaging; no religious text; motifs right for the festival and region; tricolour imagery follows the Flag Code. | festival_sheet set | Flag Code of India 2002; Emblems and Names Act 1950 | |
| C11 `retouch-decline-list` | The request is not on the decline list: body shape, skin colour, age or gender change; removal of a permanent feature without the person's written request; adding or removing people presented as the real event; face reconstruction presented as a true likeness; removing another owner's watermark; product features it does not have; structural property changes; before-and-after where the sector forbids it. | photo-fix | `agency/retouching/README.md` | |

## After generation

| Id | Check | Applies when | Rule referenced | verify_by |
| --- | --- | --- | --- | --- |
| C12 `text-letter-by-letter` | Every string read letter by letter against the brief. No added copy, however decorative. | any | house rule | |
| C13 `no-invented-badges` | No invented badges, seals, awards, star ratings, certification marks or sponsor strips. | any | ASCI; house rule | |
| C14 `no-lookalike-background-text` | No readable background text that resembles a real brand, a phone number or an address. | any | house rule | |
| C15 `platform-policy` | No before-and-after body imagery where the platform restricts it; no implied personal attributes; no fake interface elements such as play buttons. | social, ads | Meta and Google ad policies | |
| C16 `disclosure-label` | Disclosure label for realistic generated imagery where the platform, the sector or the client requires one. Property enhancements and restorations carry their disclosure line. | realistic output; property; restoration | platform rules; client disclosure policy | |
| C17 `rights-to-deliver` | The client receives files we are entitled to deliver: no stock elements without licence; source licences on file; internal-use-only sources not redistributed. | any | `_sources/SOURCES.md` | |
| C18 `mandatory-text-rendered` | Mandatory text from C03 is present and legible in the final asset or its live-text layer. | industry set | as C03 | |

## Sign-off

| Field | |
| --- | --- |
| job_id | |
| checked_by | |
| second_person | |
| date | |
| ids_passed | |
| ids_failed_and_why | |
