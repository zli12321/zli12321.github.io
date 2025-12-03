---
title:          "Semantically-Aware Rewards for Open-Ended R1 Training in Free-Form Generation"
date:           2025-06-18 00:01:00 +0800
selected:       true
pub:            "Preprint"
# pub_pre:        "Submitted to "
# pub_post:       'Under review.'
# pub_last:       ' <span class="badge badge-pill badge-publication badge-success">Oral</span>'
pub_date:       "2025"

abstract: >-
  Evaluating open-ended long-form generation is challenging because it is hard to define what clearly separates good from bad outputs. Existing methods often miss key aspects like coherence, style, or relevance, or are biased by pretraining data, making open-ended long-form evaluation an underexplored problem. To address this gap, we propose PrefBERT, a scoring model for evaluating open-ended long-form generation in GRPO and guiding its training with distinct rewards for good and bad outputs. Trained on two response evaluation datasets with diverse long-form styles and Likert-rated quality, PrefBERT effectively supports GRPO by offering better semantic reward feedback than traditional metrics ROUGE-L and BERTScore do. Through comprehensive evaluations, including LLM-as-a-judge, human ratings, and qualitative analysis, we show that PrefBERT, trained on multi-sentence and paragraph-length responses, remains reliable across varied long passages and aligns well with the verifiable rewards GRPO needs. Human evaluations confirm that using PrefBERT as the reward signal to train policy models yields responses better aligned with human preferences than those trained with traditional metrics.

cover:          /assets/images/covers/freeFormR1.png

authors:
  - Zongxia Li
  - Yapei Chang
  - Yuhang Zhou
  - Xiyang Wu
  - Zichao Liang
  - Yoo Yeon Sung
  - Jordan Lee Boyd-Graber

links:
  Paper: https://arxiv.org/abs/2506.15068
  Code: https://github.com/zli12321/free-form-grpo
  
  
---
