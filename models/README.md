# Model weights (not in Git)

Place trained checkpoints here (mounted into Docker at runtime):

- `general_best_model/` — config.json, tokenizer files, `model.safetensors`
- `medical_best_model/`
- `legal_best_model/`

Without these files the API starts but NER inference will not run until weights are present.
