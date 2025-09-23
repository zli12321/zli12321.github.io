---
title:          "VideoHallu: Evaluating and Mitigating Multi-modal Hallucinations for Synthetic Videos"
date:           2025-05-02 00:01:00 +0800
selected:       true
pub:            "Neurips"
# pub_pre:        "Submitted to "
# pub_post:       'Under review.'
# pub_last:       ' <span class="badge badge-pill badge-publication badge-success">Oral</span>'
pub_date:       "2025"

abstract: >-
  Synthetic video generation with foundation models has gained attention for its realism and wide applications. While these models produce high-quality frames, they often fail to respect common sense and physical laws, resulting in abnormal content. Existing metrics like VideoScore emphasize general quality but ignore such violations and lack interpretability. A more insightful approach is using multi-modal large language models (MLLMs) as interpretable evaluators, as seen in FactScore. Yet, MLLMs' ability to detect abnormalities in synthetic videos remains underexplored. To address this, we introduce VideoHallu, a benchmark featuring synthetic videos from models like Veo2, Sora, and Kling, paired with expert-designed QA tasks solvable via human-level reasoning across various categories. We assess several SoTA MLLMs, including GPT-4o, Gemini-2.5-Pro, Qwen-2.5-VL, and newer models like Video-R1 and VideoChat-R1. Despite strong real-world performance on MVBench and MovieChat, these models still hallucinate on basic commonsense and physics tasks in synthetic settings, underscoring the challenge of hallucination. We further fine-tune SoTA MLLMs using Group Relative Policy Optimization (GRPO) on real and synthetic commonsense/physics data. Results show notable accuracy gains, especially with counterexample integration, advancing MLLMs' reasoning capabilities.

With their rapid advancements in research and growing popularity in various applications, we provide a comprehensive survey of VLMs. Specifically, we provide a systematic overview of VLMs in the following aspects:
cover:          /assets/images/covers/videohallu.png
authors:
  - Zongxia Li*
  - Xiyang Wu*
  - Yubin Qin
  - Hongyang Du
  - Guangyao Shi
  - Dinesh Manocha
  - Tianyi Zhou
  - Jordan Lee Boyd-Graber
links:
  Paper: https://arxiv.org/abs/2505.01481
  Webpage: https://wuxiyang1996.github.io/videohallu_page/
  Github:  https://github.com/zli12321/VideoHallu
  Huggingface: https://huggingface.co/datasets/IntelligenceLab/VideoHallu
  
  
---
