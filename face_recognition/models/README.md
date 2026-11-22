# Model registry and licensing gate

Selected: OpenCV Zoo YuNet 2023 detector (MIT) and full-precision SFace 2021 recognizer (Apache-2.0), with five-landmark alignment and **128-dimensional** normalized features. The actual model output is checked at runtime. `manifest.json` records official sources, fixed SHA-256 digests and the pipeline version; downloaded models and images are ignored by Git. License copies accompany local downloads.

Every model load verifies the pinned digests. A change to weights or alignment requires a new manifest version, which invalidates old gallery features. The default 0.50 cosine threshold is a provisional precision-oriented choice, not a calibrated accuracy claim. Evaluation instructions are in the pipeline README.

Library code licenses do not necessarily grant rights to pretrained weights. The [InsightFace Python package documentation](https://github.com/deepinsight/insightface/tree/master/python-package#license) distinguishes its MIT library code from pretrained models restricted to non-commercial research. Evaluate the actual selected weights and obtain suitable rights for the intended deployment before use.
