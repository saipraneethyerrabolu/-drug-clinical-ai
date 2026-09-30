# DDI model artifacts

Phase 2 contains the adapter hook for the Weighted GNN but intentionally does not
include or fabricate a trained model artifact.

For correct inference, add the exact compatible artifacts from the GNN training
pipeline, including the trained weights, node-index mapping, graph/features and
class-label mapping. The future integration phase will wire these artifacts into
`backend/app/models/gnn/ddi_model_adapter.py`.
