# Deploy on AWS (CloudShell, no key sharing) — backend + Hermes for ~$12/mo

Runs the whole backend + Hermes brain on one small **Lightsail** instance. Your **$120 credit ≈ 10 months**.
You paste commands into **AWS CloudShell** (already authenticated in your browser) — you never share keys.

> **LLM note:** a self-hosted GPU model would burn your $120 in days. This deploy points Hermes' brain at
> **Groq's free API** (it hosts open models). Get a free key at https://console.groq.com → set `GROQ_API_KEY`.

## One-time prep (2 min)
1. Push this repo to a GitHub repo of yours (private is fine), note its URL → `REPO_URL` below.
   *(No GitHub? See "Alternative: upload" at the bottom.)*
2. Get a free **Groq API key**: https://console.groq.com/keys

## Step 1 — open CloudShell
AWS console → top bar → the `>_` **CloudShell** icon. Wait for the prompt.

## Step 2 — create the instance (paste into CloudShell)
```bash
REGION=ap-south-1                 # value is ap-south-1 (Mumbai). Change the value, not the var name.

# Bundle IDs vary by region — list what's available (cheapest first) and pick the ~2GB one:
aws lightsail get-bundles --region $REGION \
  --query 'sort_by(bundles,&price)[].[bundleId,ramSizeInGb,cpuCount,price]' --output table

BUNDLE=small_3_1                                  # 2GB, ~$12/mo in ap-south-1 (verify via the table above)
                                                  # note: IDs end _3_1 not _3_0; avoid the ipv6-only ones

aws lightsail create-instances \
  --instance-names aiglass \
  --availability-zone ${REGION}a \
  --blueprint-id ubuntu_22_04 \
  --bundle-id $BUNDLE \
  --region $REGION

# wait until it's running, then open the ports the app needs
sleep 60
aws lightsail open-instance-public-ports --region $REGION --instance-name aiglass \
  --port-info fromPort=8000,toPort=8000,protocol=TCP        # backend API
aws lightsail open-instance-public-ports --region $REGION --instance-name aiglass \
  --port-info fromPort=22,toPort=22,protocol=TCP            # SSH
```

## Step 3 — get the public IP + SSH in
```bash
aws lightsail get-instance --region $REGION --instance-name aiglass \
  --query 'instance.publicIpAddress' --output text        # note this IP
aws lightsail download-default-key-pair --region $REGION \
  --query 'privateKeyBase64' --output text > key.pem && chmod 600 key.pem   # already PEM; do NOT base64 -d
ssh -o StrictHostKeyChecking=no -i key.pem ubuntu@<PUBLIC_IP>
```

## Step 4 — bootstrap (paste on the instance, after SSH)
```bash
export REPO_URL="https://github.com/<you>/aigr.git"
export GROQ_API_KEY="gsk_..."                # your Groq key
curl -fsSL "$REPO_URL/raw/main/deploy/aws/bootstrap.sh" -o bootstrap.sh 2>/dev/null \
  || { git clone "$REPO_URL" aigr && cp aigr/deploy/aws/bootstrap.sh .; }
bash bootstrap.sh
```

## Step 5 — verify
```bash
curl -s http://<PUBLIC_IP>:8000/health        # -> {"ok":true,...}
```
Point the Android app's backend URL at `http://<PUBLIC_IP>:8000` (add TLS via Caddy before real use).

## Costs / keeping it free
- Lightsail `small_3_0` ≈ **$12/mo** → **~10 months** on $120.
- Stop paying anytime: `aws lightsail delete-instance --region $REGION --instance-name aiglass`.
- **Do not** launch GPU/EC2-GPU instances for a local LLM — that's the budget trap. Use Groq.

## Alternative: upload instead of GitHub
From CloudShell (repo not on GitHub): `scp -i key.pem -r ../../aigr ubuntu@<IP>:~/aigr` then run
`bash ~/aigr/deploy/aws/bootstrap.sh` on the instance.

> These scripts are **untested by me** (I can't run AWS from here). Run them and paste any error back —
> we'll fix it together.
