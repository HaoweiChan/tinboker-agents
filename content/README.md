# Content-Builder Pipeline

A Dify workflow for analyzing podcast transcripts and generating Traditional Chinese financial news articles.

## Prerequisites

- **Docker** and **Docker Compose** must be installed
- If Docker is not installed, see [docs/INSTALL_DOCKER.md](docs/INSTALL_DOCKER.md) for installation instructions

## Setup

### 1. Setup Dify

**Option A: Using the provided script (Recommended - No Authentication)**

For local development or internal networks:

```bash
./start_rerun_dify.sh
```

This script automatically:
- Clones the Dify repository if needed
- Sets up environment variables for large content handling
- Starts all services including Marp service
- **No authentication** - direct access to `http://localhost:8001` (port 8001 by default)
- **Port Configuration**: Defaults to port 8001 to avoid conflict with port 80 and 8080. Change with `DIFY_PORT=port_number ./start_rerun_dify.sh`

**Option B: Manual setup**

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env
docker compose up -d
```

**Common Issues:**
- If you get connection errors, wait a few minutes for services to start
- Check logs: `docker compose logs api` or `docker compose logs nginx`
- Restart nginx if needed: `docker compose restart nginx`
- **PPTX base64 too large**: The script sets `CODE_MAX_STRING_LENGTH=2000000` (2M chars) to handle large PPTX files. If you still hit limits, increase it in `start_rerun_dify.sh`

**For detailed instructions without auth, see [docs/START_WITHOUT_AUTH.md](docs/START_WITHOUT_AUTH.md)**

### 1.1. Securing Your Dify Server (For Public Access)

**⚠️ IMPORTANT**: If you're exposing your Dify server to the public internet, you MUST enable authentication!

**Quick Setup:**

1. Create password file:
   ```bash
   ./setup_dify_auth.sh
   ```

2. Start Dify with authentication:
   ```bash
   ENABLE_AUTH=true ./start_rerun_dify.sh
   ```

3. Access your server - you'll be prompted for username/password

**For detailed instructions, see [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)**

### 2. Import Workflow and Get API Key

1. **Access Dify Console**: Open `http://localhost:8001` in your browser and complete initial setup (default port is 8001)
2. **Import Workflow**: 
   - Go to "Apps" → "Create App" → "Workflow"
   - Click "Import" button and upload `dify_config/latest.yml`
   - Wait for import to complete
3. **Publish the App**: 
   - In the workflow editor, click "Publish" button (top right)
   - This makes the workflow available via API/webhook
4. **Get API Key and URLs**:
   - **API Key**: Go to "Settings" → "API Keys" → Create/Copy API key
   - **Webhook URL**: In workflow editor, go to "API Access" tab → Copy "Webhook Debug URL"
     - Format: `http://localhost:8001/triggers/webhook-debug/{webhook_id}` (port 8001 by default)
   - **API Base URL**: Usually `http://localhost:8001/v1` (port 8001 by default)
5. **Save to `.env` file**:
   ```bash
   echo "DIFI_API_KEY=your_api_key_here" >> .env
   ```

## Usage

### Option 1: Webhook Trigger (Recommended)

Use the webhook endpoint for direct transcript processing:

```bash
curl -X POST "http://localhost:8001/triggers/webhook-debug/{webhook_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Your transcript text here...",
    "source": "早晨財經速解讀",
    "episode_title": "Episode Title"
  }'
```

**Using the provided script:**
```bash
./send_webhook.sh
# or
python3 test/send_webhook.py
```

### Option 2: Workflow API

Use the workflow API endpoint (requires API key):

```bash
curl -X POST "http://localhost:8001/v1/workflows/run" \
  --header "Authorization: Bearer {DIFI_API_KEY}" \
  --header "Content-Type: application/json" \
  --data-raw '{
    "inputs": {
      "transcript": "Your transcript text here...",
      "source": "早晨財經速解讀",
      "episode_title": "Episode Title"
    },
    "response_mode": "streaming",
    "user": "user-id"
  }'
```

**Using the provided script:**
```bash
python3 test/test_workflow_api.py --with-transcript
```

## Request Format

### Webhook Request

```json
{
  "transcript": "string (required) - Full podcast transcript text",
  "source": "string (optional) - Source name, e.g., '早晨財經速解讀'",
  "episode_title": "string (optional) - Episode title"
}
```

### Workflow API Request

```json
{
  "inputs": {
    "transcript": "string (required)",
    "source": "string (optional)",
    "episode_title": "string (optional)"
  },
  "response_mode": "streaming" | "blocking",
  "user": "string - User identifier"
}
```

## Output Format

### Webhook Response

The webhook returns immediately (async mode) with a JSON response:

```json
{
  "status": "success",
  "data": {
    "content": "{{#markdown_transform_node.markdown_output#}}"
  },
  "metadata": {
    "source": "{{#start_node.source#}}",
    "episode_title": "{{#start_node.episode_title#}}"
  }
}
```

**Note**: Since the webhook runs asynchronously, the template variables are returned immediately. The actual content is processed in the background. To get the final markdown immediately, use the Workflow API with `"response_mode": "blocking"` (see below).

### Workflow API Response (Streaming)

The API returns Server-Sent Events (SSE) stream:

```
data: {"event":"workflow_started",...}
data: {"event":"node_started",...}
data: {"event":"text_chunk","data":{"text":"# Article Title\n\n..."}}
data: {"event":"node_finished",...}
data: {"event":"workflow_finished",...}
```

### Getting the Final Markdown Output

**From Webhook (Async):**
- The webhook returns immediately with template variables
- The workflow processes in the background
- To get the actual content, you need to poll the workflow status or use the API endpoint

**From Workflow API (Blocking Mode - Recommended):**
```bash
curl -X POST "http://localhost:8001/v1/workflows/run" \
  --header "Authorization: Bearer {DIFI_API_KEY}" \
  --header "Content-Type: application/json" \
  --data-raw '{
    "inputs": {
      "transcript": "...",
      "source": "...",
      "episode_title": "..."
    },
    "response_mode": "blocking",
    "user": "user-id"
  }'
```
- Response contains `data.outputs.markdown_report` with the final markdown string
- **Important**: Use `"response_mode": "blocking"` - streaming mode has a known issue where inputs don't map correctly to webhook trigger nodes
- This is the recommended method to get immediate results

**From Workflow API (Streaming Mode):**
- ⚠️ **Known Issue**: Streaming mode (`"response_mode": "streaming"`) has a bug where inputs don't map correctly to webhook trigger nodes, resulting in empty/null values
- **Workaround**: Use `"response_mode": "blocking"` instead, or use the webhook URL directly for async processing
- If streaming is required, you may need to modify the workflow to use a Start node instead of a Webhook Trigger node

### Markdown Format

The output follows the content guidelines:
- **Language**: Traditional Chinese (繁體中文)
- **Stock Tickers**: `[Display Name](#ticker:SYMBOL)` - e.g., `[台積電](#ticker:2330)`
- **Tags**: `[Tag Name](#tag:TAG_NAME)` - e.g., `[半導體](#tag:Semiconductor)`
- **Structure**: H1 title, H2 sections, H3 subsections
- **Content**: Financial/market focus only

## Example

```bash
# Using webhook (simplest)
python3 test/send_webhook.py

# Using API with transcript
python3 test/test_workflow_api.py --with-transcript
```

## Workflow Structure

```
Start → Extractor → Clusterer → Writer → Markdown Transform → End
                         ↓
                   MARP_Writer → Marp Converter → End
                         ↓                ↓
                   Events to Markdown    Flask Service (PPTX)
```

### Pipeline Flow:

1. **Extractor**: Extracts events with sentence indices from transcript
2. **Sentence Clusterer**: Groups sentences into financial events
3. **Writer**: Generates structured JSON article in Traditional Chinese
4. **MARP_Writer** (Parallel): Generates Marp-formatted presentation slides
5. **Markdown Transform**: Transforms article JSON to Markdown format
6. **Marp Converter**: Transforms slides JSON to Marp markdown and calls Flask service for PPTX conversion
7. **Events to Markdown**: Creates event list with timestamps
8. **End**: Returns markdown article, events list, Marp markdown, and base64-encoded PPTX

## PowerPoint Generation

The pipeline now includes automatic PowerPoint generation using Marp. A parallel branch generates presentation slides from the same financial events used for article writing.

### How It Works

1. **MARP_WRITER Node**: 
   - Receives the same financial events as the Writer node
   - Generates concise, visual-friendly slide content
   - Creates structured JSON with slide headings and bullet points
   - Optimized for presentation format (3-5 key points per slide)

2. **Marp Converter Node**:
   - Transforms JSON to Marp markdown format
   - Adds Marp directives (theme, pagination, headers)
   - Calls Marp Flask Service to convert to PPTX
   - Returns both Marp markdown and base64-encoded PPTX

3. **Marp Flask Service**:
   - Containerized service running on port 5004
   - Uses Marp CLI to convert markdown to PowerPoint
   - Returns base64-encoded PPTX data

### Output Format

The workflow returns additional fields in the End node output:

- `marp_markdown`: The Marp-formatted markdown source
- `pptx_base64`: Base64-encoded PowerPoint file
- `pptx_filename`: Generated filename (e.g., `presentation_1234567890.pptx`)
- `pptx_conversion_status`: Status of PPTX conversion ("success" or error message)

### Extracting the PowerPoint File

**Using Python:**
```python
import base64
import json

# Parse the workflow response
response = json.loads(workflow_output)
pptx_base64 = response['data']['outputs']['pptx_base64']

# Decode and save
pptx_data = base64.b64decode(pptx_base64)
with open('presentation.pptx', 'wb') as f:
    f.write(pptx_data)
```

**Using bash:**
```bash
# Extract pptx_base64 from JSON response and decode
echo $PPTX_BASE64 | base64 -d > presentation.pptx
```

### Marp Service Details

**Endpoints:**
- `GET /health` - Health check endpoint
- `POST /convert` - Convert Marp markdown to PPTX
  - Request: `{"markdown": "..."}`
  - Response: `{"success": true, "pptx_base64": "...", "filename": "...", "size_bytes": ...}`
- `POST /upload` - Legacy endpoint for uploading markdown files

**Service Management:**
```bash
# View logs
docker logs -f marp-flask-service

# Restart service
docker restart marp-flask-service

# Stop service
docker stop marp-flask-service

# Check health
curl http://localhost:5004/health
```

**Startup:**
The Marp service is automatically started by `./start_rerun_dify.sh` and runs in a Docker container connected to the Dify network.

You can also start/restart the Marp service independently:
```bash
./start_marp_service.sh
```

This is useful if you need to restart only the Marp service without affecting the Dify server.

## Troubleshooting

- **Empty transcript**: Ensure JSON is properly escaped (use provided scripts)
- **502 Bad Gateway**: Restart nginx: `docker compose restart nginx`
- **API Key errors**: Verify key in `.env` file matches Dify console
- **Workflow not found**: Ensure workflow is published in Dify console
- **PPTX conversion fails**: Check Marp service logs: `docker logs marp-flask-service`
- **Marp service not responding**: Ensure service is running: `docker ps | grep marp-flask-service`
- **Empty pptx_base64**: Check `pptx_conversion_status` field for error details
