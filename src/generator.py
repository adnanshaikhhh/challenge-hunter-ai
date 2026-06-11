#!/usr/bin/env python3
"""
Challenge Hunter AI - Project File Generator
Generates 5 project files for approved opportunities:
1. README.md - Project overview and setup
2. architecture.md - System design and tech stack
3. task_list.md - Day-by-day development plan
4. demo_plan.md - Demo script and talking points
5. submission_checklist.md - Final submission checklist
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta

# =============================================================================
# DATABASE
# =============================================================================

DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'opportunities.db'))


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    return conn


# =============================================================================
# FILE GENERATORS
# =============================================================================

def generate_readme(opp, analysis):
    """Generate README.md content"""
    name = opp.get('name', 'Project')
    prize = opp.get('prize_usd', 0)
    deadline = opp.get('deadline', 'TBD')
    source = opp.get('source', 'Unknown')
    eligibility = opp.get('eligibility', 'Global')
    difficulty = opp.get('difficulty', 'medium')
    ai_policy = opp.get('ai_policy', 'allowed')

    project = analysis.get('recommended_project', {})
    project_name = project.get('name', 'my-project')
    concept = project.get('concept', 'An innovative AI-powered solution')
    tech_stack = project.get('tech_stack', ['Python', 'Flask', 'React'])
    key_features = project.get('key_features', [])
    estimated_days = project.get('estimated_build_days', 5)

    tech_stack_str = ', '.join(tech_stack)

    content = f"""# {project_name}

> {concept}

## 🏆 Challenge
{name} | ${prize:,} Prize | Deadline: {deadline}

## 🎯 Problem It Solves
[Describe the core problem your project addresses in 2-3 sentences]

## ✨ Key Features

{chr(10).join(f"- {feat}" for feat in key_features)}

- Clean, responsive UI with modern design
- Real-time functionality with no lag
- Production-ready with proper error handling
- Comprehensive documentation

## 🛠 Tech Stack

{tech_stack_str}

## 📋 Requirements

- Python 3.11+
- Node.js 18+
- npm or yarn
- Modern web browser

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/{project_name}.git
cd {project_name}
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd client
npm install
```

### 4. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Run the Application

```bash
# Terminal 1 - Backend
python app.py

# Terminal 2 - Frontend
cd client
npm run dev
```

### 6. Open in Browser

Navigate to: http://localhost:3000

## 📁 Project Structure

```
{project_name}/
├── client/              # Frontend (React)
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom hooks
│   │   └── utils/       # Utility functions
│   └── package.json
├── server/              # Backend (Python)
│   ├── app.py          # Main application
│   ├── routes/         # API routes
│   └── models/         # Data models
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── architecture.md     # System architecture
```

## 🎬 Demo

Watch our demo video: [Link to demo video]

### Demo Highlights

1. **Problem Statement** - What challenge does this solve?
2. **Live Demo** - Watch the app in action
3. **Technical Deep Dive** - How it was built
4. **Future Roadmap** - What's next?

## 🧪 Testing

```bash
# Run backend tests
pytest server/tests/

# Run frontend tests
cd client && npm test
```

## 📝 Submission Details

- **Challenge:** {name}
- **Prize:** ${prize:,}
- **Deadline:** {deadline}
- **Source:** {source}
- **Difficulty:** {difficulty.capitalize()}
- **AI Policy:** {ai_policy.capitalize()}

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - feel free to use this project for your submission.

## 🙏 Acknowledgments

- Challenge Hunter AI for opportunity discovery
- The {source} team for organizing this competition
- Open source contributors and the developer community

---

**Built with ❤️ for {name}**
**Estimated build time: {estimated_days} days**
"""

    return content


def generate_architecture(opp, analysis):
    """Generate architecture.md content"""
    name = opp.get('name', 'Project')
    prize = opp.get('prize_usd', 0)
    difficulty = opp.get('difficulty', 'medium')

    project = analysis.get('recommended_project', {})
    project_name = project.get('name', 'my-project')
    concept = project.get('concept', 'An innovative AI-powered solution')
    tech_stack = project.get('tech_stack', ['Python', 'Flask', 'React'])

    # Separate frontend and backend tech
    backend_tech = [t for t in tech_stack if t.lower() in ['python', 'fastapi', 'flask', 'django', 'node.js', 'express', 'postgresql', 'mysql', 'mongodb', 'redis', 'docker', 'kubernetes', 'celery']]
    frontend_tech = [t for t in tech_stack if t.lower() in ['react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt', 'tailwind css', 'html', 'css', 'javascript', 'typescript']]

    if not backend_tech:
        backend_tech = ['Python', 'FastAPI']
    if not frontend_tech:
        frontend_tech = ['React', 'Tailwind CSS']

    content = f"""# {project_name} - Architecture

## 📖 Overview

{concept}

This is a full-stack application built for **{name}** ({prize:,} prize pool).

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│                   (React + Tailwind CSS)                     │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Components │  │    Pages     │  │   State (Zustand)│  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API GATEWAY                            │
│                   (FastAPI + CORS)                           │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Routes    │  │  Middleware  │  │  Auth (JWT)      │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   DATA LAYER    │ │   AI SERVICES   │ │   EXTERNAL      │
│  (PostgreSQL)   │ │  (OpenAI/Claude)│ │   APIs          │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 🛠 Tech Stack Justification

### Backend: {', '.join(backend_tech)}

| Technology | Justification |
|------------|---------------|
| **Python** | Excellent AI/ML ecosystem, rapid development |
| **FastAPI** | High performance, automatic docs, type safety |
| **PostgreSQL** | Reliable relational data, JSON support |
| **Docker** | Consistent deployment, easy scaling |

### Frontend: {', '.join(frontend_tech)}

| Technology | Justification |
|------------|---------------|
| **React** | Component reuse, vast ecosystem, great DX |
| **Tailwind CSS** | Rapid styling, consistent design system |
| **Vite** | Fast builds, instant server start |

## 📊 Data Flow

### User Request Flow

```
User Action → React Component → API Request → FastAPI Route → Database → Response → UI Update
```

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/data` | Fetch main data |
| POST | `/api/analyze` | AI-powered analysis |
| PUT | `/api/update` | Update record |

## 🔐 Security

- JWT-based authentication for all protected routes
- CORS configured for specific origins only
- Input validation on all endpoints
- SQL injection prevention via parameterized queries
- XSS prevention via React's built-in escaping

## 📈 Performance Optimizations

1. **Database Indexing** - Fast queries on common lookups
2. **Caching** - Redis for frequently accessed data
3. **Lazy Loading** - Load components on demand
4. **Code Splitting** - Smaller JavaScript bundles

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t {project_name}:latest .

# Run container
docker run -p 8000:8000 {project_name}:latest
```

### Production Environment

- **Frontend**: Vercel / Netlify
- **Backend**: Railway / Render / Fly.io
- **Database**: Railway Postgres / Supabase
- **Monitoring**: Sentry + DataDog

## 🔮 Future Roadmap

1. **Phase 1** - Core features, MVP launch
2. **Phase 2** - User authentication, profiles
3. **Phase 3** - AI-powered recommendations
4. **Phase 4** - Mobile app (React Native)

## 📐 Diagrams

### Component Hierarchy

```
App
├── Layout
│   ├── Header
│   ├── Sidebar
│   └── Footer
├── Pages
│   ├── Dashboard
│   ├── Analysis
│   └── Settings
└── Components
    ├── Cards
    ├── Forms
    └── Modals
```

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
"""

    return content


def generate_task_list(opp, analysis):
    """Generate task_list.md content"""
    name = opp.get('name', 'Project')
    deadline = opp.get('deadline', 'TBD')
    difficulty = opp.get('difficulty', 'medium')

    project = analysis.get('recommended_project', {})
    estimated_days = project.get('estimated_build_days', 5)

    # Adjust tasks based on difficulty
    task_multipliers = {'easy': 0.8, 'medium': 1.0, 'hard': 1.3}
    multiplier = task_multipliers.get(difficulty, 1.0)
    days = max(3, int(estimated_days * multiplier))

    content = f"""# {name} - Development Task List

**Total Estimated Days:** {days}
**Deadline:** {deadline}
**Difficulty:** {difficulty.capitalize()}

---

## 📅 Day 1: Setup & Foundation

### Morning (3 hours)
- [ ] Set up project repository (Git initialized)
- [ ] Configure development environment
- [ ] Install all dependencies (backend + frontend)
- [ ] Set up database and schema
- [ ] Create .env files with config

### Afternoon (4 hours)
- [ ] Build basic backend structure (routes, models)
- [ ] Set up frontend project structure
- [ ] Create base layout component
- [ ] Implement basic routing
- [ ] Verify both servers run without errors

### Evening (2 hours)
- [ ] Review Day 1 work
- [ ] Write basic README setup section
- [ ] Push initial commit

---

## 📅 Day 2: Core Features

### Morning (3 hours)
- [ ] Design database schema for core data
- [ ] Build main API endpoints (CRUD)
- [ ] Connect frontend to backend
- [ ] Build main page layouts

### Afternoon (4 hours)
- [ ] Implement core feature #1
- [ ] Implement core feature #2
- [ ] Add form handling and validation
- [ ] Style components with Tailwind

### Evening (2 hours)
- [ ] Test all features manually
- [ ] Fix any bugs found
- [ ] Push progress commit

---

## 📅 Day 3: AI Integration & Polish

### Morning (3 hours)
- [ ] Integrate AI API (OpenAI/Claude/Anthropic)
- [ ] Build AI-powered features
- [ ] Handle API errors gracefully
- [ ] Add loading states

### Afternoon (4 hours)
- [ ] Polish UI/UX - all pages styled
- [ ] Add responsive design
- [ ] Implement dark/light mode if time
- [ ] Add animations and transitions

### Evening (2 hours)
- [ ] Cross-browser testing
- [ ] Mobile responsiveness check
- [ ] Push polished commit

---

## 📅 Day 4: Demo Preparation

### Morning (3 hours)
- [ ] Record demo video (2-3 minutes)
- [ ] Prepare slides or demo script
- [ ] Practice demo presentation
- [ ] Prepare backup screenshots

### Afternoon (4 hours)
- [ ] Final feature polish
- [ ] Documentation pass
- [ ] Write comprehensive README
- [ ] Add architecture diagram

### Evening (2 hours)
- [ ] Submit initial draft if allowed
- [ ] Review submission requirements
- [ ] Final code cleanup

---

## 📅 Day 5: Testing & Submission

### Morning (3 hours)
- [ ] Full regression testing
- [ ] Test on multiple browsers
- [ ] Test edge cases
- [ ] Fix any remaining bugs

### Afternoon (4 hours)
- [ ] Prepare submission materials:
  - [ ] Project description
  - [ ] Demo video link
  - [ ] Screenshots
  - [ ] Setup instructions
- [ ] Deploy to production/hosting
- [ ] Test live deployment

### Evening (2 hours)
- [ ] Final review of submission
- [ ] Submit before deadline
- [ ] Celebrate! 🎉

---

## 🎯 Daily Checklist

Before ending each day:
- [ ] All code committed to git
- [ ] No console errors in browser
- [ ] README updated if needed
- [ ] Ready to demo today's work

## 🚨 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI API rate limits | Cache responses, add fallback |
| Deadline pressure | Skip "nice to have" features |
| Demo fails | Have screenshots as backup |
| Mobile issues | Test early, focus on desktop |

---

## ✅ Submission Requirements Checklist

- [ ] Working demo deployed
- [ ] Demo video (2-3 minutes)
- [ ] README complete
- [ ] Screenshots ready
- [ ] Source code submitted
- [ ] Project description written

**Good luck! 🚀**
"""

    return content


def generate_demo_plan(opp, analysis):
    """Generate demo_plan.md content"""
    name = opp.get('name', 'Project')
    prize = opp.get('prize_usd', 0)
    source = opp.get('source', 'Unknown')

    project = analysis.get('recommended_project', {})
    project_name = project.get('name', 'my-project')
    key_features = project.get('key_features', [])
    demo_approach = project.get('demo_approach', 'Minute-by-minute demo script')

    content = f"""# {name} - Demo Plan

**Project:** {project_name}
**Prize:** ${prize:,}
**Demo Duration:** 2-3 minutes

---

## 🎬 Demo Script (3 Minutes)

### Minute 1: Introduction (60 seconds)

**Slide: Title + Problem Statement**

> "Hi everyone, I'm here to present [Project Name] - [One sentence concept]."

**Key Points to Cover:**
1. Introduce yourself briefly (5 seconds)
2. State the problem you're solving (20 seconds)
   - "The challenge today is..."
   - "Current solutions are lacking because..."
3. Present your solution (20 seconds)
   - "We built [Name] to solve this"
   - "Our key insight was..."

**Transition:** "Let me show you how it works..."

---

### Minute 2: Live Demo (60 seconds)

**Open the application live**

**Demo Flow:**
1. Show the main dashboard (10 seconds)
   - Point out key metrics or features
2. Demonstrate primary feature #1 (15 seconds)
   - Show it working with real data
   - Highlight what makes it special
3. Demonstrate primary feature #2 (15 seconds)
   - Different from #1, show breadth
4. Show AI-powered feature (15 seconds)
   - This is the differentiator
   - Show real AI output

**Demo Do's:**
- ✅ Use realistic data/examples
- ✅ Show clear before/after
- ✅ Pause for effect on key moments
- ✅ Make it look effortless

**Demo Don'ts:**
- ❌ Don't rush - take your time
- ❌ Don't show error states
- ❌ Don't fumble with mouse
- ❌ Don't go too deep technically

**If Demo Fails:**
> "Here's a screenshot of the feature working..." (switch to screenshots backup)

---

### Minute 3: Technical Highlights + Wrap-up (60 seconds)

**Technical Points to Mention:**
1. Tech stack used (10 seconds)
   - "Built with {', '.join(project.get('tech_stack', ['Python', 'FastAPI', 'React']))}"
2. Key technical achievement (15 seconds)
   - Something impressive about implementation
3. Future roadmap (10 seconds)
   - "Next steps would be..."

**Closing:**
> "And that's [Project Name]. We built this in [X] days with a focus on [key quality]. Thank you!"

**Q&A Prep:**
- Know your architecture decisions
- Be ready to discuss scaling
- Know your approximate cost to run

---

## 📊 What to Highlight

### Primary Features (Must Show)
{chr(10).join(f"{i+1}. {feat}" for i, feat in enumerate(key_features[:3]))}

### Secondary Features (If Time)
- User-friendly interface
- Fast performance
- Clean code architecture

### Technical Highlights
- AI integration
- Real-time updates
- Responsive design

---

## 🎯 Judge Talking Points

1. **Innovation** - What's novel about your approach?
2. **Impact** - How many people does this help?
3. **Feasibility** - Is this actually buildable?
4. **Presentation** - Did you tell a compelling story?
5. **Completeness** - Does it work end-to-end?

---

## 🛡 Backup Plan

### If Live Demo Fails:
1. **Screenshots** - Have 3-4 screenshots ready
2. **Loom Video** - Pre-recorded backup video
3. **Local Demo** - Run locally if cloud is down

### If Questions You Can't Answer:
> "That's a great question. We focused on [what you know] and haven't explored that area yet."

---

## 📋 Demo Checklist (Before You Start)

- [ ] Deployed to production URL
- [ ] Demo account logged in
- [ ] Browser tested, no console errors
- [ ] Screenshots saved locally
- [ ] Backup video recorded
- [ ] Timer tested (3 minutes)
- [ ] Slides ready (if using)

- [ ] Water nearby
- [ ] Mic check done
- [ ] Screen share tested
- [ ] Notifications disabled

---

## 🎥 Recording Tips

1. **Resolution:** 1080p minimum
2. **Frame Rate:** 30fps
3. **Audio:** Use mic, not built-in
4. **File Size:** Under 100MB for upload
5. **Format:** MP4 (H.264)

---

## ⏱ Time Management

| Segment | Target | Max |
|---------|--------|-----|
| Intro | 60s | 75s |
| Demo | 60s | 90s |
| Close | 60s | 75s |
| **Total** | **3 min** | **4 min** |

---

**Practice your demo at least 3 times before the real thing! 🎯**
"""

    return content


def generate_submission_checklist(opp, analysis):
    """Generate submission_checklist.md content"""
    name = opp.get('name', 'Project')
    prize = opp.get('prize_usd', 0)
    deadline = opp.get('deadline', 'TBD')
    source = opp.get('source', 'Unknown')
    eligibility = opp.get('eligibility', 'Global')

    project = analysis.get('recommended_project', {})
    project_name = project.get('name', 'my-project')
    tech_stack = project.get('tech_stack', [])

    content = f"""# {name} - Submission Checklist

**Project:** {project_name}
**Prize:** ${prize:,}
**Deadline:** {deadline} (ALL TIMES IN YOUR LOCAL TIMEZONE)
**Source:** {source}
**Eligibility:** {eligibility}

---

## ⚠️ CRITICAL REMINDERS

1. **Submit at least 2 hours before deadline** - last-minute issues happen
2. **Read ALL submission requirements** - disqualification is real
3. **Verify your submission** - check links work, files are complete
4. **Keep a copy of everything** - local backup + cloud backup

---

## 📝 Required Materials

### ✅ Project Submission Form

- [ ] Project name entered correctly
- [ ] Short description (150-280 characters)
- [ ] Full description written compellingly
- [ ] All required fields completed
- [ ] Eligibility confirmed

### ✅ Source Code

- [ ] Code uploaded (ZIP or GitHub repo)
- [ ] All dependencies in requirements.txt
- [ ] README included
- [ ] License file included
- [ ] No sensitive data (API keys removed)

### ✅ Demo Video

- [ ] Video recorded (2-3 minutes)
- [ ] Audio clear and audible
- [ ] Video under file size limit
- [ ] Uploaded successfully
- [ ] Link works publicly

### ✅ Screenshots

- [ ] Main dashboard screenshot
- [ ] Feature demonstration screenshots (2-3)
- [ ] Mobile responsiveness screenshot
- [ ] All images properly labeled

### ✅ Documentation

- [ ] README.md complete
- [ ] Setup instructions clear
- [ ] Architecture.md included
- [ ] License specified (MIT recommended)

---

## 🚫 Common Mistakes to AVOID

| Mistake | Prevention |
|---------|------------|
| Forgot to submit | Set 3 alarms + calendar reminder |
| Wrong file format | Read requirements twice |
| Dead link in video | Test all links 24h before |
| Expired API key | Have backup/demo mode |
| Submitted after deadline | Submit 2 hours early minimum |
| Incomplete fields | Use this checklist |

---

## 🔍 Final Review (Do This 24 Hours Before Deadline)

### 24 Hours Before

- [ ] All code committed and pushed
- [ ] README updated with correct links
- [ ] Demo video uploaded and accessible
- [ ] Screenshots all look professional
- [ ] Project description proofread
- [ ] Eligibility requirements double-checked

### 2 Hours Before Deadline

- [ ] Log into submission platform
- [ ] Start submission process
- [ ] Upload all files
- [ ] Fill all fields
- [ ] Preview everything
- [ ] Submit!

### After Submitting

- [ ] Confirmation email received
- [ ] Check submission link publicly
- [ ] Verify file sizes are within limits
- [ ] Screenshot confirmation for records

---

## 📦 Submission Package Contents

```
{project_name}/
├── submission.zip
│   ├── source-code/
│   │   ├── (all project files)
│   │   └── README.md
│   ├── demo-video.mp4
│   ├── screenshots/
│   │   ├── dashboard.png
│   │   ├── feature-1.png
│   │   └── feature-2.png
│   └── additional-materials/
│       └── (any extra docs)
├── live-url.txt (https://your-demo-url.com)
├── video-url.txt (https://youtube.com/watch?v=xxx)
└── notes.txt (anything to tell judges)
```

---

## 📞 Emergency Contacts

| Contact | Email | Phone |
|---------|-------|-------|
| Challenge Organizer | [Check {source} website] | - |
| Technical Support | [If provided] | - |
| Your Email | [your@email.com] | - |

---

## 📅 Timeline

| Deadline Type | Date/Time |
|--------------|-----------|
| **Final Deadline** | {deadline} |
| **Personal Buffer** | 2 hours before |
| **Internal Review** | 24 hours before |
| **Code Freeze** | 12 hours before |

---

## ✅ Final Sign-Off

Before hitting submit, check each of these:

- [ ] I've read the complete rules
- [ ] My project meets all eligibility requirements
- [ ] I have rights to all code and assets
- [ ] The demo video is under the time limit
- [ ] All links are public and working
- [ ] No API keys or secrets in code
- [ ] I've tested the submission on a different browser
- [ ] I have a backup of everything

---

**You are READY. Submit with confidence! 🚀**

---

## 🎉 Post-Submission

After you submit:

1. Take a break - you earned it!
2. Share on LinkedIn/Twitter (use competition hashtag)
3. Add to your portfolio
4. Write a blog post about what you learned
5. Thank anyone who helped you

**Good luck! You've got this! 💪**
"""

    return content


# =============================================================================
# MAIN GENERATOR CLASS
# =============================================================================

class ProjectFileGenerator:
    """Generates project files for approved opportunities"""

    FILES = [
        ('README.md', generate_readme),
        ('architecture.md', generate_architecture),
        ('task_list.md', generate_task_list),
        ('demo_plan.md', generate_demo_plan),
        ('submission_checklist.md', generate_submission_checklist),
    ]

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH

    def generate_all(self, opportunity_id, opportunity):
        """Generate all 5 project files for an opportunity"""
        # Parse analysis_json if it's a string
        analysis = opportunity.get('analysis_json', {})
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except json.JSONDecodeError:
                analysis = {}

        # Merge opportunity data into analysis for recommended_project
        if 'recommended_project' not in analysis:
            analysis['recommended_project'] = {}

        conn = get_db_connection()
        cursor = conn.cursor()

        files_created = 0

        for filename, generator_func in self.FILES:
            try:
                content = generator_func(opportunity, analysis)

                # Save to database
                cursor.execute("""
                    INSERT INTO project_files (opportunity_id, filename, content)
                    VALUES (?, ?, ?)
                """, (opportunity_id, filename, content))
                files_created += 1

                print(f"  📄 Generated: {filename}")

            except Exception as e:
                print(f"  ⚠️  Failed to generate {filename}: {e}")
                continue

        conn.commit()
        conn.close()

        print(f"  ✅ Created {files_created} project files for opportunity #{opportunity_id}")
        return files_created

    def get_files_for_opportunity(self, opportunity_id):
        """Get list of files for an opportunity"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT filename, created_at FROM project_files
            WHERE opportunity_id = ?
            ORDER BY created_at
        """, (opportunity_id,))

        files = cursor.fetchall()
        conn.close()

        return [dict(row) for row in files]

    def get_file_content(self, opportunity_id, filename):
        """Get content of a specific file"""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT content FROM project_files
            WHERE opportunity_id = ? AND filename = ?
        """, (opportunity_id, filename))

        row = cursor.fetchone()
        conn.close()

        return row['content'] if row else None


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("Project File Generator - Challenge Hunter AI")
    print("Use app.py to generate files for approved opportunities.")