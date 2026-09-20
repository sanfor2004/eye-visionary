# Model licensing and attribution

The project code and documentation are separate from downloaded model weights. Do not redistribute model caches in this repository or release artifacts without checking each model's terms.

## Florence-2-large

The Hugging Face model card identifies `microsoft/Florence-2-large` as MIT licensed. Keep the model's license and attribution with any distribution of the weights or derivative package.

## InsightFace buffalo_l

The InsightFace model zoo documents `buffalo_l` and states that its pretrained model packs are intended for non-commercial research use. Commercial deployments must complete a licensing review and obtain appropriate rights before enabling the model in a product.

## Project obligations

- Keep `models/manifest.json` synchronized with the selected model revision.
- Record model name, revision, provider, and embedding dimension in persisted analysis results.
- Print or publish attribution notices during packaging.
- Do not use generated test fixtures to identify real people.
- Recheck upstream licenses before changing model versions.
