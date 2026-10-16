# Hardware options — buy-assembled vs DIY (July 2026)

The user wants: HUD display + camera + speaker + self-hostable/reconfigurable backend + discreet.
**No single product delivers all of these** — the most discreet HUD glasses drop the camera & speaker
for privacy/size; the ones that keep camera+speaker+HUD are not invisible. Physics, not budget.

Our **backend + Hermes orchestrator is hardware-agnostic** and reusable across every option below.

| Product | HUD | Camera | Speaker | Own backend | Discreet | Price (India landed*) | Notes |
|---|---|---|---|---|---|---|---|
| **Brilliant Labs Halo** ⭐ | ✅ color, peripheral | ⚠️ basic | ✅ bone-conduction | ✅✅ open, vibe-code apps | ⚠️ everyday-ish, thin | $349→$399 (~₹40k) | Succeeds Frame. Ships ~Jul 20 2026. Best all-round match. |
| Brilliant Labs Frame | ✅ 0.23" 640×400, 20° FOV | ✅ nose-bridge cam | ❌ BT earbuds | ✅✅ most hackable | ⚠️ chunky | ~₹38k | Older; sharper display but no speaker. |
| Mentra Live (MentraOS) | ❌ | ✅✅ 12MP 119° | ✅ stereo, 3 mics | ✅✅ BT SDK, offline, self-host | ⚠️ visible cam | $349 (~₹40k) | Best camera + fully self-hostable, but no HUD. |
| Even Realities G2 | ✅✅ most discreet | ❌ | ❌ | ⚠️ Even Hub SDK | ✅✅ normal eyewear | ~₹65k+ | Best "undetectable + display" but no camera/speaker. |
| Vuzix Z100 | ✅ waveguide mono | ❌ | ⚠️ | ⚠️ MentraOS | ✅ lightweight | ~₹forty-something k | Display-only, MentraOS compatible. |
| **DIY XIAO ESP32-S3** | ❌ (no cheap HUD) | ✅ | ✅ | ✅✅✅ 100% yours | ⚠️ purpose frame | ~₹5k | Cheapest, fully yours, but adding a HUD is the hard part. |

<sub>*Landed ≈ price + ~30–40% India import duty/GST; these ship internationally.</sub>

## Software layers worth building on (not from scratch)
- **MentraOS** — 100% open-source smart-glasses OS + SDK + app store; supports Even Realities, Vuzix,
  Mentra Live. Apps can run offline and avoid any Mentra cloud → point them at our backend.
  https://github.com/Mentra-Community/MentraOS
- **Brilliant Labs SDK** — open hardware + software, Python/Flutter; run your own AI (Whisper/GPT/local).
  https://brilliant.xyz
- **Omi / OpenGlass** — the DIY reference designs we started from.

## Takeaway
- Want HUD + camera + speaker + own backend, buy-assembled → **Brilliant Labs Halo**.
- Want best camera + own backend, no HUD → **Mentra Live**.
- Want maximum discreet HUD, no camera → **Even Realities G2**.
- Want cheapest + fully yours, no HUD → **DIY XIAO** (current `firmware/` path).
- In ALL cases the `backend/` + Hermes brain is the same reusable core.
