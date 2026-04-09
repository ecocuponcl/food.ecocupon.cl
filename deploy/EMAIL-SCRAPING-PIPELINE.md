# 📧 EMAIL SCRAPING PIPELINE — n8n Workflow

## Purpose
Automatically process incoming emails → LLM intent analysis → Add qualified leads to pipeline

## n8n Workflow JSON
Save as: `/root/n8n-workflows/40-email-lead-scraper.json`

## Workflow Structure

```
[IMAP Trigger] → [Extract Body] → [LLM Intent Analysis]
    ↓
[If Intent = Lead] → [Score Lead] → [Add to leads.json]
    ↓                                    ↓
[If Intent = Spam] → [Discard]    [Push to Kaggle (auto)]
```

## Implementation

### Node 1: IMAP Email Trigger
- Type: `n8n-nodes-base.imap`
- Trigger: Every 5 minutes
- Server: Your IMAP server
- Authentication: OAuth2 or App Password

### Node 2: Extract Email Body
- Type: `n8n-nodes-base.function`
- Code:
```javascript
const emailBody = $input.item.json.body || '';
const subject = $input.item.json.subject || '';
const from = $input.item.json.from || '';

return [{
  json: {
    email_body: emailBody,
    subject: subject,
    from_email: from,
    timestamp: new Date().toISOString()
  }
}];
```

### Node 3: LLM Intent Analysis
- Type: `n8n-nodes-base.httpRequest`
- Method: POST
- URL: `https://llm.smarterbot.store/v1/chat/completions`
- Headers:
  ```
  Authorization: Bearer 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
  Content-Type: application/json
  ```
- Body:
```json
{
  "model": "qwen/qwen-turbo",
  "messages": [
    {"role": "system", "content": "You are a lead qualification assistant. Analyze the email and respond with JSON: {\"is_lead\": true/false, \"score\": 0-100, \"product_interest\": \"CLAWBOT/Hosting/Kiosk/Other\", \"summary\": \"brief summary\"}"},
    {"role": "user", "content": "Subject: {{ $json.subject }}\nFrom: {{ $json.from_email }}\nBody: {{ $json.email_body }}\n\nIs this a potential lead for SmarterBOT? Respond with JSON only."}
  ],
  "max_tokens": 200
}
```

### Node 4: If/Else Branch
- Condition: `$json.is_lead === true`
- If true → Node 5 (Add to leads.json)
- If false → Node 6 (Discard/Archive)

### Node 5: Add to leads.json (via Webhook)
- Type: `n8n-nodes-base.httpRequest`
- Method: POST
- URL: `http://127.0.0.1:8004/store-contacto`
- Body:
```json
{
  "nombre": "{{ $json.from_email }}",
  "email": "{{ $json.from_email }}",
  "telefono": "",
  "mensaje": "{{ $json.summary }}",
  "product": "{{ $json.product_interest }}",
  "source": "email-scraper",
  "revenue_score": {{ $json.score }}
}
```

### Node 6: Mark as Spam
- Type: `n8n-nodes-base.function`
- Code: Log to spam file or archive

## Deployment

1. Import workflow to n8n:
   ```bash
   cp 40-email-lead-scraper.json /root/n8n-workflows/
   ```

2. Configure IMAP credentials in n8n UI

3. Activate workflow

## Expected Result

- Every 5 minutes, checks emails
- Analyzes intent with LLM
- Qualified leads added to pipeline automatically
- Auto-export to Kaggle on next cycle
- HOT leads trigger Telegram alert
