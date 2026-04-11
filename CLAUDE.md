# CLAUDE.md — Tractatus Eval

## Wiki 连接

本项目关联到个人 LLM Wiki，wiki 中维护了全局画像、项目上下文和定制交互提示词。

**每次会话启动时，请读取以下文件获取最新上下文：**

1. `/Users/tianjiesun/my-wiki/wiki/meta/persona.md` — Tianjie 全局画像（思维模式、兴趣图谱、知识版图）
2. `/Users/tianjiesun/my-wiki/wiki/meta/prompts/tractatus-eval.md` — 本项目定制交互提示词
3. `/Users/tianjiesun/my-wiki/wiki/projects/tractatus-eval.md` — 本项目在 wiki 中的最新状态

**当你在本项目中做了重要技术决策时**，主动提示 Tianjie：
"要不要把这个决策同步到 wiki？我可以帮你写一份摘要存到 `raw/from-code/`。"

**Wiki 路径**：`/Users/tianjiesun/my-wiki`

---

## This Project: Tractatus Eval

### What It Is
A Benchmark for Spatial Embodied Logic in Large Language Models. 个人独立研究项目。

- **GitHub**: https://github.com/AlexFlanker/tractatus-eval
- **Stage**: 基础版本已完成

### Philosophical Foundation
项目以维特根斯坦命名——不是随意的，是哲学立场声明。LLM 的认知天花板被人类语言的既有边界锁死（维特根斯坦 "语言的边界就是世界的边界"），空间推理是测量这个边界的具体领域。深层框架：验证-生成不对称（P vs NP 视角）。

### Who You're Working With
Tianjie Sun — Backend software engineer, 7 years experience, currently at hireEZ. Cornell ECE MEng. 链式深潜型思考者——从具体问题出发沿一条线钻到元层面。

### Technical Profile
- **Core stack**: TypeScript, Node.js, Python
- **AI/LLM**: NVIDIA GenAI LLM Professional certified
- **Dev environment**: macOS (Apple Silicon), VS Code + Claude Code

### Coding Preferences
- **Style**: Concise, functional where possible
- **Comments**: Minimal — code should be self-documenting
- **Research context**: 工程背景非学术出身，实验设计方法论可能需要额外支持

### Working Style
- 喜欢从哲学/概念层面理解项目意义，不只是"做一个 benchmark"
- 讨论中可以引入 Wheeler、哥德尔、Hofstadter 等思想资源
- 会在开放性问题上明确押注，可以直接问他立场
- 最终要把思考转化为可执行的行动

### Related Projects
- **ddia-fde-system** (`/Users/tianjiesun/Desktop/ddia-fde-system`) — DDIA 学习系统
- **interview-dojo** (`/Users/tianjiesun/Desktop/FDE_Portfolio_2026/interview_dojo`) — 面试准备平台

### FDE Competitiveness Role
Tractatus-Eval 在 FDE 面试中的定位：**开源代表作**。三层构成：底层理论（NVIDIA GenAI 认证）+ 开源代表作（Tractatus-Eval）+ 生产经验（ATS 集成）。
