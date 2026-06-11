---
permalink: /
title: "About me"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

I am a fourth-year PhD candidate in Computer Science at the University of Maryland, College Park, in the [CLIP Lab](https://wiki.umiacs.umd.edu/clip/index.php/Main_Page), advised by [Jordan Boyd-Graber](http://users.umiacs.umd.edu/~ying/) and co-advised by [Lichao Sun](https://lichao-sun.github.io). My research develops methods that make vision-language models and agents more capable through post-training, more autonomous through self-evolution, and more useful through tighter collaboration with humans.

Research Focus
======
1. **Model Post-Training** — Reinforcement learning and reward design for vision-language models, including self-rewarding via reasoning decomposition, semantically-aware open-ended rewards, and hallucination-targeted alignment for image and video understanding.

2. **Self-Evolving Agents** — Autonomous agents that bootstrap their own capabilities from minimal or zero human-curated data, spanning self-evolving multimodal reasoning, co-evolving decision-and-skill agents for long-horizon tasks, and exploration-guided visual reasoning.

3. **Human-AI Collaboration** — How humans and AI systems collaborate to optimize real-world workflows, from LLM-assisted annotation and interactive topic exploration to robust automatic evaluation metrics that faithfully reflect human judgment.

News
======
<style>
  .news-scroll { max-height: 340px; overflow-y: auto; margin-top: 0.5rem; padding: 0 1rem; border: 1px solid #e1e4e8; border-radius: 8px; }
  .news-table { width: 100%; border-collapse: collapse; margin: 0; font-size: 0.95rem; }
  .news-table td { padding: 0.6rem 0.5rem; vertical-align: top; border: none; line-height: 1.45; }
  .news-table tr + tr td { border-top: 1px solid #f0f0f0; }
  .news-date { white-space: nowrap; font-weight: 700; color: #333; width: 1%; padding-right: 1rem !important; }
</style>
<div class="news-scroll" markdown="0">
<table class="news-table">
<tr><td class="news-date">May 1, 2026</td><td><a href="https://github.com/Moms-Organic-Agent-Lab/comfyclaw" target="_blank">ComfyClaw</a> is released! An agentic harness for skill-evolving image generation workflows.</td></tr>
<tr><td class="news-date">Apr 29, 2026</td><td><a href="https://arxiv.org/abs/2604.20987" target="_blank">COS-PLAY</a> is released! Co-evolving LLM decision and skill bank agents for long-horizon tasks.</td></tr>
<tr><td class="news-date">Apr 7, 2026</td><td><a href="https://arxiv.org/abs/2604.05333" target="_blank">Graph-of-Skills</a> is released! Dependency-aware structural retrieval for massive agent skills.</td></tr>
<tr><td class="news-date">Mar 10, 2026</td><td><a href="https://arxiv.org/abs/2603.09206" target="_blank">MM-Zero</a> is released! Self-evolving VLMs from zero data using multi-role RL training.</td></tr>
<tr><td class="news-date">Feb 20, 2026</td><td><a href="https://firstframego.github.io/" target="_blank">FFGO</a>, <a href="https://arxiv.org/abs/2511.15661" target="_blank">VisPlay</a>, and <a href="https://arxiv.org/abs/2511.18373" target="_blank">MASS</a> are accepted to CVPR 2026.</td></tr>
<tr><td class="news-date">Feb 8, 2026</td><td>R-Zero and Vision-SR1 are accepted to ICLR 2026.</td></tr>
<tr><td class="news-date">Nov 20, 2025</td><td><a href="https://firstframego.github.io/" target="_blank">FFGO</a> is released! Customize your video with our FFGO LoRA adapters.</td></tr>
<tr><td class="news-date">Nov 19, 2025</td><td><a href="https://arxiv.org/abs/2511.15661" target="_blank">VisPlay</a> is released! Learn how to evolve VLMs with just images.</td></tr>
<tr><td class="news-date">Sep 20, 2025</td><td>VideoHallu is accepted to NeurIPS 2025.</td></tr>
<tr><td class="news-date">Aug 22, 2025</td><td>I finished my internship at Tencent AI Lab, Bellevue, mentored by <a href="https://wyu97.github.io" target="_blank">Wenhao Yu</a>, working on self-evolving VLMs and LLMs.</td></tr>
<tr><td class="news-date">Jul 22, 2025</td><td>I received a research compute grant from Lambda Labs.</td></tr>
<tr><td class="news-date">Aug 22, 2024</td><td>I finished my internship at Adobe Document Intelligence Lab, focusing on improving LLM automatic evaluations for downstream training.</td></tr>
</table>
</div>

Selected Publications
======
<div class="pub-preview" markdown="0">
{% assign sel_links = "/publication/2026-05-01-comfyclaw,/publication/2026-04-24-vision-sr1,/publication/2026-03-10-mm-zero,/publication/2025-12-01-videohallu,/publication/2026-06-01-ffgo,/publication/2026-04-07-graph-of-skills,/publication/2026-04-29-cosplay" | split: "," %}
{% for link in sel_links %}
{% assign post = site.publications | where: "permalink", link | first %}
{% if post %}
<div class="pub-item">
  {% if post.header.teaser %}<img class="pub-thumb" src="{{ post.header.teaser | prepend: '/images/' | relative_url }}" alt="">{% endif %}
  <div class="pub-text">
    <a class="pub-title" href="{{ post.url | relative_url }}">{{ post.title }}</a>
    {% if post.authors %}<div class="pub-authors">{{ post.authors | replace: 'Zongxia Li', '<strong>Zongxia Li</strong>' }}</div>{% endif %}
    <div class="pub-venue">{{ post.venue }}</div>
    <div class="pub-links">
      {% if post.paperurl %}<a href="{{ post.paperurl }}" target="_blank">[paper]</a>{% endif %}
      {% if post.projecturl %}<a href="{{ post.projecturl }}" target="_blank">[webpage]</a>{% endif %}
      {% if post.codeurl %}<a href="{{ post.codeurl }}" target="_blank">[code]</a>{% endif %}
    </div>
  </div>
</div>
{% endif %}
{% endfor %}
</div>

[See all publications &raquo;]({{ '/publications/' | relative_url }})
{: .pub-see-all}

Popular Community Projects
======
<style>
  .open-source-projects { display: flex; flex-direction: column; gap: 0.8rem; margin-top: 0.5rem; }
  .open-source-projects .os-card { border: 1px solid #e1e4e8; border-radius: 8px; padding: 0.8rem 1rem; }
  .open-source-projects .os-title { font-weight: 700; font-size: 1rem; text-decoration: none; }
  .open-source-projects .os-star { float: right; font-size: 0.85rem; color: #6a737d; white-space: nowrap; }
  .open-source-projects .os-desc { margin: 0.4rem 0 0; font-size: 0.9rem; color: #6a737d; }
</style>
<div class="open-source-projects">
  <div class="os-card">
    <a href="https://github.com/OpenLAIR/dr-claw" target="_blank" rel="noopener" class="os-title"><i class="fab fa-github"></i> Dr. Claw: Your AI Research Assistant</a>
    <span class="os-star" data-github-repo="OpenLAIR/dr-claw"><i class="fa fa-star"></i> &mdash;</span>
    <p class="os-desc">A super AI lab with massive AI doctors as assistants &mdash; the best IDE for research powered by AI.</p>
  </div>
  <div class="os-card">
    <a href="https://github.com/zli12321/Vision-Language-Models-Overview" target="_blank" rel="noopener" class="os-title"><i class="fab fa-github"></i> Large Vision-Language Models: A Survey &amp; Benchmark Collection</a>
    <span class="os-star" data-github-repo="zli12321/Vision-Language-Models-Overview"><i class="fa fa-star"></i> &mdash;</span>
    <p class="os-desc">A comprehensive, continuously updated collection of VLM benchmarks, RL alignment methods, and applications.</p>
  </div>
</div>

<script src="{{ '/assets/js/github_stars.js' | relative_url }}"></script>
