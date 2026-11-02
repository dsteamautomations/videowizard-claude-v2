# Compliance checklist

Run before generation and again before delivery. The ids that apply go in the answer's `compliance_flags`; the operator alone decides. Each law named here is checked against its current text at its first real use.

## General: every category

### Before generation

| Id | Check |
| --- | --- |
| C01 `claims-sourced` | Every factual claim shown or narrated has a written source. |
| C07 `no-alcohol-tobacco` | Not produced. (India: Cable TV Rules; COTPA) |
| C08 `no-third-party-marks` | No third-party logos, competitor product shapes, franchise characters or recognisable protected designs. |
| C09 `no-lookalike` | No public figure or lookalike, and no generated person who resembles a real, identifiable adult or child, including a person described only in words. |
| C10 `symbols-respected` | Religious and national symbols are used respectfully and as local law requires: no deities on products, footwear, food or packaging. (India: Flag Code 2002; Emblems and Names Act 1950) |

### After generation

| Id | Check |
| --- | --- |
| C12 `text-letter-by-letter` | Every string read letter by letter against `exact_text`. No added words, however decorative. |
| C13 `no-invented-badges` | No invented badge, seal, award, rating or certification (RULEBOOK's no-invention rule). |
| C14 `no-lookalike-background-text` | No readable background text that looks like a real brand, phone number or address. |
| C16 `disclosure-label` | A disclosure label on realistic generated pictures and clips where the platform, the sector or the client requires one. Every video take also carries Google's invisible watermark. |
| C17 `rights-to-deliver` | Every file delivered is ours to deliver: no unlicensed stock, source licences on file, internal-use-only sources not passed on. |

## For documentary-explainer

- C11 `no-staged-events`: never add or remove people or events in a picture presented as the real event.

## For advertisement-product

| Id | Check |
| --- | --- |
| C02 `no-superlatives` | No unsupported "best", "No. 1", "guaranteed", "100 percent". (ASCI code) |
| C15 `platform-policy` | Also for social-ugc: no before-and-after body imagery where the platform restricts it, no implied personal attributes, no fake interface elements such as play buttons. (The ad platforms' own policies) |

### For healthcare

- C04 `no-health-outcome-claims`: no cure, treatment or outcome claim; no before-and-after for conditions. (Drugs and Magic Remedies Act 1954; Drugs and Cosmetics Act)

### For education

- C05 `no-education-guarantees`: no guaranteed placement, marks or ranks. (ASCI education guidelines)

### For finance

- C06 `no-return-promises`: no promised returns. (SEBI and RBI advertising rules)

### For real estate

- A property shown enhanced or restored carries its disclosure line (C16); no structural change to a real property.

## Not available yet

- **C03 / C18 mandatory text:** the sector's required wording (real estate: the RERA registration number; food: the FSSAI licence number; finance: the risk disclaimer) present and legible. Not checked today: the job form's mandatory text is always none.
