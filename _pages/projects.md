---
layout: archive
title: "Projects"
permalink: /projects/
author_profile: true
---

A selection of my pinned open-source repositories. Live star counts are pulled directly from GitHub.

<style>
  .repo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 1rem; }
  .repo-card { display: flex; flex-direction: column; border: 1px solid #e1e4e8; border-radius: 8px; padding: 1rem 1.1rem; transition: box-shadow .15s ease, border-color .15s ease; }
  .repo-card:hover { border-color: #c8ccd1; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
  .repo-card .repo-head { display: flex; align-items: baseline; justify-content: space-between; gap: .5rem; }
  .repo-card .repo-name { font-weight: 700; font-size: 1.02rem; text-decoration: none; }
  .repo-card .repo-star { font-size: .85rem; color: #6a737d; white-space: nowrap; }
  .repo-card .repo-owner { font-size: .8rem; color: #6a737d; margin: .15rem 0 0; }
  .repo-card .repo-desc { margin: .55rem 0 0; font-size: .9rem; color: #57606a; line-height: 1.45; }
</style>

<div class="repo-grid">
  <div class="repo-card">
    <div class="repo-head">
      <a class="repo-name" href="https://github.com/zli12321/Vision-Language-Models-Overview" target="_blank" rel="noopener"><i class="fab fa-github"></i> Vision-Language-Models-Overview</a>
      <span class="repo-star" data-github-repo="zli12321/Vision-Language-Models-Overview"><i class="fa fa-star"></i> &mdash;</span>
    </div>
    <p class="repo-owner">zli12321</p>
    <p class="repo-desc">A comprehensive, continuously updated collection of VLM benchmarks, RL alignment methods, and applications.</p>
  </div>

  <div class="repo-card">
    <div class="repo-head">
      <a class="repo-name" href="https://github.com/zli12321/Vision-SR1" target="_blank" rel="noopener"><i class="fab fa-github"></i> Vision-SR1</a>
      <span class="repo-star" data-github-repo="zli12321/Vision-SR1"><i class="fa fa-star"></i> &mdash;</span>
    </div>
    <p class="repo-owner">zli12321</p>
    <p class="repo-desc">Self-rewarding VLM that splits reasoning into visual perception and language reasoning, improving without human labels or external rewards.</p>
  </div>

  <div class="repo-card">
    <div class="repo-head">
      <a class="repo-name" href="https://github.com/zli12321/FFGO-Video-Customization" target="_blank" rel="noopener"><i class="fab fa-github"></i> FFGO-Video-Customization</a>
      <span class="repo-star" data-github-repo="zli12321/FFGO-Video-Customization"><i class="fa fa-star"></i> &mdash;</span>
    </div>
    <p class="repo-owner">zli12321</p>
    <p class="repo-desc">First-frame-guided video content customization with only 20&ndash;50 training examples via lightweight LoRA adapters.</p>
  </div>

  <div class="repo-card">
    <div class="repo-head">
      <a class="repo-name" href="https://github.com/Chengsong-Huang/R-Zero" target="_blank" rel="noopener"><i class="fab fa-github"></i> R-Zero</a>
      <span class="repo-star" data-github-repo="Chengsong-Huang/R-Zero"><i class="fa fa-star"></i> &mdash;</span>
    </div>
    <p class="repo-owner">Chengsong-Huang</p>
    <p class="repo-desc">Self-evolving reasoning LLM trained entirely from zero human-curated data via a co-evolving challenger&ndash;solver curriculum.</p>
  </div>

  <div class="repo-card">
    <div class="repo-head">
      <a class="repo-name" href="https://github.com/OpenLAIR/dr-claw" target="_blank" rel="noopener"><i class="fab fa-github"></i> Dr. Claw</a>
      <span class="repo-star" data-github-repo="OpenLAIR/dr-claw"><i class="fa fa-star"></i> &mdash;</span>
    </div>
    <p class="repo-owner">OpenLAIR</p>
    <p class="repo-desc">A super AI lab with massive AI doctors as assistants &mdash; an IDE for research powered by AI.</p>
  </div>

  <div class="repo-card">
    <div class="repo-head">
      <a class="repo-name" href="https://github.com/davidliuk/graph-of-skills" target="_blank" rel="noopener"><i class="fab fa-github"></i> Graph-of-Skills</a>
      <span class="repo-star" data-github-repo="davidliuk/graph-of-skills"><i class="fa fa-star"></i> &mdash;</span>
    </div>
    <p class="repo-owner">davidliuk</p>
    <p class="repo-desc">Dependency-aware structural retrieval that builds an executable skill graph offline and retrieves skill bundles at inference time.</p>
  </div>
</div>

<script src="{{ '/assets/js/github_stars.js' | relative_url }}"></script>
