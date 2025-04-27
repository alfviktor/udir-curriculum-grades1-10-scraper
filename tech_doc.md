# Purpose
Provide each Lokalbank‑medlem en rask, lokal kopi av all offentlig kunde‑ og produktinformasjon (FAQ‑sider, PDF‑prislister, vilkår) som grunnlag for en demo‑chat.  

---
## 1 · Mål
* **Samle** åpent innhold fra ett bankdomene.
* **Lagre** som JSON / markdown klar for vektor‑indeksering.
* **Kjør** hele prosessen på < 15 min per bank.

---
## 2 · Hovedsteg
| Nr. | Steg | Verktøy | Kommentar |
|---|---|---|---|
| 1 | Last ned sitemap / bruteforce URL‑liste | `scrapy` + `robots.txt` respekt | Unngå innloggede / admin‑stier |
| 2 | Hent HTML + PDF | `aiohttp` + `pdfminer.six` | Parallell, maks 8 samtidige requests |
| 3 | Ekstrahér tekst | BeautifulSoup / PDF‑extract | Fjerner navigasjon, cookie‑bannere |
| 4 | Del opp i chunks | Simple splitter (<= 512 tokens) | Beholder overskrift som metadata |
| 5 | Lagre til disk | JSON Lines | Felt: `bank`, `url`, `title`, `chunk`, `tokens` |

---
## 3 · Mappe‑struktur (per bank)
```
flekkefjord/
  raw_html/
  raw_pdf/
  chunks.jsonl
```

---
## 4 · Sikkerhet & Compliance
* **Kun offentlige sider** – ingen cookies eller persondata.
* **Kryptert trafikk (HTTPS)** når vi laster ned.
* **Kilde‑lenke lagres** for transparens i chat‑svar.
---
_Rev. 26 Apr 2025 – Alf Viktor_