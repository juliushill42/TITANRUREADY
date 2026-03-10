# TitanU OS Installation Guide

## 📥 Installation

### System Requirements
- **Operating System:** Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 2GB free space
- **Python:** 3.8 or higher (for development)
- **Node.js:** 16.x or higher (for development)

### Quick Install (Recommended)

1. **Download the latest release** from the TitanU OS releases page
2. **Run the installer** (`TitanU OS Setup X.X.X.exe` for Windows)
3. **Follow the installation wizard** prompts
4. **Launch TitanU OS** from your desktop or start menu

### Portable Installation

1. **Download the portable version** (zip file)
2. **Extract to your desired location** (USB drive recommended)
3. **Run `TitanU OS.exe`** directly from the extracted folder
4. **No installation required** - runs completely self-contained

### Development Installation

For developers who want to build from source:

```bash
# Clone the repository
git clone https://github.com/titanu-os/titanu-os.git
cd titanu-os

# Install dependencies
pip install -r requirements.txt
cd frontend/electron && npm install

# Run in development mode
# Windows:
scripts\dev.bat

# Linux/Mac:
./scripts/dev.sh
```

---

## 🎉 Post-Installation: What to Expect

### First Launch Experience

When you first launch TitanU OS v3.2, here's what you'll experience:

#### 1. **Genesis Key Authentication**
- **What you'll see:** A premium full-screen modal requesting your Genesis Key
- **What to do:** Enter your Genesis Key in the format: `TITANU-GENESIS-XXX-XXXXXX`
- **What happens:** The system validates your key and grants access to TitanU OS
- **Don't have a key?** Contact the TitanU team for Genesis access information

#### 2. **Boot Sequence**
- **What you'll see:** A cinematic boot sequence with the TITAN logo and system initialization
- **What happens:** The system loads core components and establishes secure connections
- **Duration:** Typically 5-10 seconds

#### 3. **Main Interface**
- **What you'll see:** A sleek cyberpunk terminal interface with multiple panels
- **Available panels:**
  - **Chat Panel** (center) - Main conversation area with TITAN
  - **Memory Panel** (left) - View and manage memory entries
  - **Files Panel** (right) - Browse and manage your files
  - **System Tools** (top-right) - Settings, export logs, restart

---

## ⚠️ Important: v3.2 Feature Limitations

### Features Currently Available
✅ **Full Conversational AI** - Chat naturally with TITAN about any topic  
✅ **Memory System** - Create, view, edit, and delete memory entries  
✅ **File Management** - Browse directories, read files, and manage your data  
✅ **Web Scraping** - Fetch and summarize content from URLs  
✅ **Voice Support** - Optional voice transcription capabilities  
✅ **100% Local Processing** - Everything runs on your machine, no internet required  

### Features Temporarily Disabled (Returning in v3.3)
⏸️ **Custom Agent Creation** - The ability to create specialized AI agents from natural language descriptions  
⏸️ **Conversational Agents** - Interacting with specialized agent personalities like Research Agent, Code Agent, etc.  
⏸️ **Agent Templates** - The 4 built-in agent templates (Research, Code, Writing, Data Analyst)  

### Why Are These Features Disabled?

We've temporarily disabled agent creation and conversational agents in v3.2 to:

1. **Ensure Maximum Stability** - Focus on perfecting core conversational AI
2. **Enhance Performance** - Optimize response times for primary features
3. **Prepare for v3.3** - Rebuild the agent system with improved capabilities
4. **Maintain Quality** - Deliver the best possible experience with available features

### What This Means for You

**You can still:**
- Have full conversations with TITAN about any topic
- Use the memory system to store and recall information
- Browse and read your files
- Scrape and summarize web content
- Enjoy fast, stable performance

**You cannot (until v3.3):**
- Create custom agents with `@create agent ...`
- Invoke specialized agents with `@agent_name`
- Use agent-specific commands or templates

---

## 🔄 Timeout Behavior

### What Happens During Timeouts

TitanU OS v3.2 includes enhanced timeout handling for a better user experience:

**When a request takes longer than expected:**
- You'll see the message: *"The request took longer than expected. TITAN is still stable — please try again."*
- The system remains stable and responsive
- No error states or crashes occur
- You can immediately try your request again

**Why this happens:**
- Complex queries may require more processing time
- Local LLM models have variable response times
- System is processing your request in the background

**What to do:**
1. Wait a moment and try your request again
2. Simplify your query if possible
3. Check that your LLM model is properly loaded
4. The system is designed to handle this gracefully

---

## 🔑 Genesis Key Activation

### What is a Genesis Key?

A Genesis Key is your exclusive access pass to TitanU OS, available only to the first 100 founding operators. It unlocks:

- **Immediate Access** - Use TitanU OS today
- **Premium Features** - Custom agent creation (v3.3)
- **Priority Support** - Direct assistance from our team
- **Lifetime Updates** - All future versions included
- **Exclusive Community** - Join the founding operators network

### How to Activate Your Genesis Key

1. **Launch TitanU OS** - The Genesis Key modal appears automatically
2. **Enter your key** - Type or paste your Genesis Key
3. **Click "Validate Key"** - The system verifies your key
4. **Success!** - You're granted access to TitanU OS

### Genesis Key Format

**Format:** `TITANU-GENESIS-XXX-XXXXXX`

**Examples:**
- `TITANU-GENESIS-001-ABC123`
- `TITANU-GENESIS-042-FOUND1`
- `TITANU-GENESIS-100-ZYX789`

**Where to find your key:**
- Email from the TitanU team
- Genesis membership card
- Your Genesis operator welcome package

### Troubleshooting Genesis Key Issues

**"Invalid Genesis Key" error:**
- Double-check the key format and spelling
- Ensure hyphens are in the correct positions
- Verify your key hasn't expired
- Contact support if issues persist

**Lost your key?**
- Contact the TitanU support team
- Provide your operator information for verification
- We'll help you recover your access

---

## 📅 Upgrade Path to v3.3

### What's Coming in v3.3

**Planned Release:** Q1 2026

**Restored Features:**
- ✅ Custom agent creation from natural language
- ✅ Conversational agent interactions
- ✅ All 4 agent templates (Research, Code, Writing, Data Analyst)
- ✅ Enhanced agent capabilities and performance

**New Features:**
- 🆕 Improved agent stability and response times
- 🆕 Additional agent templates
- 🆕 Agent sharing and community features
- 🆕 Advanced customization options

### How to Upgrade

**Automatic Updates:**
- TitanU OS will notify you when v3.3 is available
- Click "Update Now" to download and install automatically
- Your settings and data will be preserved

**Manual Update:**
- Download v3.3 from the releases page
- Run the installer (it will update your existing installation)
- Launch and enjoy the restored features

**Genesis Key Compatibility:**
- Your Genesis Key works with all v3.x versions
- No need to re-enter your key when upgrading
- All premium benefits carry over automatically

---

## 🛠️ Troubleshooting

### Common Issues and Solutions

**"TITAN is not responding":**
- Check that the backend is running
- Try restarting the application
- Verify your LLM model is properly configured

**"Cannot connect to backend":**
- Ensure no firewall is blocking the connection
- Check that ports are available
- Try restarting your computer

**Features not working as expected:**
- Remember v3.2 limitations (see above)
- Check that you're using the correct commands
- Refer to the `/help` command in the app

**Performance issues:**
- Close unnecessary applications to free RAM
- Ensure you meet the system requirements
- Consider using a smaller LLM model

### Getting Help

- **In-app Help:** Type `/help` in the chat interface
- **Documentation:** Check the docs folder for detailed guides
- **Community:** Join the TitanU community forums
- **Support:** Contact the TitanU support team directly

---

## 🎓 Tips for Best Experience

### Getting Started
1. **Start with simple conversations** - Get familiar with TITAN's capabilities
2. **Use the memory system** - Store important information for later recall
3. **Try web scraping** - Fetch content from URLs for summarization
4. **Explore the interface** - Check out all panels and features

### Maximizing v3.2
- **Focus on core features** - Master conversational AI and memory
- **Be patient with timeouts** - The system is stable, just retry
- **Use natural language** - TITAN understands conversational prompts
- **Keep it local** - Enjoy the privacy of 100% local processing

### Preparing for v3.3
- **Learn the basics now** - Master core features before agents return
- **Provide feedback** - Help us improve the agent system
- **Stay updated** - Watch for announcements about v3.3
- **Keep your Genesis Key safe** - You'll need it for all future versions

---

**Need more help?** Check the main README.md file or type `/help` in the TitanU OS interface.