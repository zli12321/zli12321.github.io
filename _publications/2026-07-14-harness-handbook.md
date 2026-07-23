---
title: "Harness Handbook: Making Evolving Agent Harnesses Readable, Navigable, and Editable"
collection: publications
category: preprints
permalink: /publication/2026-07-14-harness-handbook
authors: 'Ruhan Wang, Yucheng Shi, Zongxia Li, Zhongzhi Li, Yue Yu, Junyao Yang, Kishan Panaganti, Haitao Mi, Dongruo Zhou, Leoweiliang'
excerpt: 'A handbook synthesized via static analysis and LLM-assisted structuring that maps agent-harness behaviors to source code, paired with Behavior-Guided Progressive Disclosure for efficient, localized edits.'
date: 2026-07-14
venue: 'Preprint'
paperurl: 'https://arxiv.org/abs/2607.13285'
projecturl: 'https://ruhan-wang.github.io/Harness-Handbook/'
codeurl: 'https://github.com/Ruhan-Wang/Harness_Handbook'
citation: 'Ruhan Wang, Yucheng Shi, Zongxia Li, Zhongzhi Li, Yue Yu, Junyao Yang, Kishan Panaganti, Haitao Mi, Dongruo Zhou, Leoweiliang. (2026). "Harness Handbook: Making Evolving Agent Harnesses Readable, Navigable, and Editable." <i>Preprint</i>.'
header:
  teaser: harness-handbook.png
---

Modifying an AI agent harness requires developers to pinpoint the exact code locations responsible for a given behavior, which is hard as harnesses evolve. We introduce the Harness Handbook, synthesized automatically from a harness codebase via static analysis and LLM-assisted structuring, that maps behaviors to source code. We pair it with Behavior-Guided Progressive Disclosure, a technique that guides agents from high-level behaviors down to relevant implementation details. On modification requests drawn from open-source harnesses, this approach improves behavior localization and token efficiency, particularly for scattered sites, rarely executed paths, and cross-module interactions.

[arXiv](https://arxiv.org/abs/2607.13285) | [Code](https://github.com/Ruhan-Wang/Harness_Handbook) | [Blog](https://ruhan-wang.github.io/Harness-Handbook/)
