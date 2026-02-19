from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="PosteriorAI/godavari-telugu-llama2-7B",
    local_dir="telugullama",
    local_dir_use_symlinks=False,
    resume_download=True
)
