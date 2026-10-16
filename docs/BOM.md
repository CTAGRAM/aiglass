# Bill of Materials — Tier 1 "Discreet AI Glasses"

Indian-market pricing, indicative as of **July 2026** (excl. shipping; prices fluctuate).
Sources: [Robu.in](https://robu.in), [Robocraze](https://robocraze.com),
[Robokits](https://robokits.co.in), [Thingbits](https://www.thingbits.in), [Amazon.in](https://www.amazon.in).

## Hardware — the device

| Part | Why it's here | Price (₹) | Example source |
|---|---|---|---|
| Seeed **XIAO ESP32-S3 Sense** | Brain: OV2640 camera + PDM mic, WiFi/BLE, USB-C LiPo charging | 1,900 – 2,300 | Robu.in / Robocraze |
| 3.7V ~400mAh **LiPo battery** | Power | 150 – 250 | Robu.in (₹156 confirmed) |
| **MAX98357A** I²S amplifier | Drives the speaker over I²S | 90 – 300 | Robokits (₹89) / Robu.in |
| **Bone-conduction transducer** 8Ω 1W *(or 8Ω mini speaker ₹50)* | Open-ear audio out | 250 – 400 | Thingbits |
| microSD 32GB *(optional)* | Offline audio buffer | 250 – 400 | Amazon.in |
| JST connectors, silicone wire, tactile button, misc | Wiring | 150 – 300 | Robu.in |
| **Sleek frame** (thick-temple 3D-print, or gut a ₹2–5k audio-glasses shell) | Hides all electronics; camera dot near the hinge | 300 – 1,500 | print shop / Amazon.in |
| **Device subtotal** | | **≈ 3,500 – 5,500** | |

> **No display — by choice (the sleek "image 2" build).** A see-through HUD forces a visible box + prism in
> front of the lens; that's exactly what makes DIY glasses look like a science project. Dropping it is what
> lets the glasses look normal. Instead the AI **speaks** answers through the bone-conduction speaker and
> shows detail in the phone app — the same audio-first model as Ray-Ban Meta and the original Omi, neither
> of which has a display. (A cheap reflected-OLED HUD is possible but can never be sleek at this tier, so
> it's out of scope — see git history if you ever want it back.)

> The board is ~half the total. It's the one part not to cheap out on — the **Sense** variant
> is what packs camera + mic into one 21×17.5mm module. The plain XIAO ESP32-S3 (no camera) is
> ~₹1,300 but useless for this build.

## Tools — one-time (skip what you own)

| Tool | Price (₹) |
|---|---|
| Soldering iron + multimeter combo kit | 300 – 700 |
| Solder wire + flux (if not bundled) | 100 – 200 |
| Wire strippers / cutters | 150 – 250 |
| Tweezers | 80 – 150 |
| Helping-hands / PCB holder | 250 – 500 |
| Hot-glue gun + Kapton tape / heat-shrink | 300 – 550 |
| USB-C data cable (flashing) | 150 |
| **Tools subtotal** | **≈ 1,200 – 2,500** |

## Infra — recurring

| Item | Cost |
|---|---|
| Linux VPS (backend + Hermes sandbox) — Hostinger / Contabo / DigitalOcean | ₹350 – 800 / month |
| LLM — Groq free tier / Claude / OpenAI API, or local model on VPS | ₹0 – ~1,000 / month by usage |
| Domain (optional) | ~₹800 / year |

## Totals

| Scenario | One-time | Monthly |
|---|---|---|
| Own no tools | ≈ ₹5,000 – 8,000 | ≈ ₹400 – 800 |
| Already have soldering tools | ≈ ₹3,500 – 5,500 | ≈ ₹400 – 800 |

## Notes / substitutions

- **Cheapest audio path:** skip bone-conduction, use a ₹50 8Ω mini speaker + the ₹89 MAX98357A.
- **No 3D printer?** Gut a cheap opaque acetate frame, or use a local print shop (~₹200–500/job).
- **Skip microSD** for v1 if you always stream to the phone; add it later for offline capture.
- Buy the board from **one** trusted seller (Robu.in / Robocraze / Fab.to.Lab) — grey-market XIAO
  clones exist and the camera ribbon is fragile.
