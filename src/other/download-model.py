from huggingface_hub import snapshot_download

if __name__ == '__main__':
    model_dir = snapshot_download(repo_id='opendatalab/pdf-extract-kit-1.0', max_workers=30,
                                  allow_patterns='models/Layout/YOLO/*')
    model_dir = model_dir + '/models'
    print(f'model_dir is: {model_dir}')
