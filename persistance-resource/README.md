


## Experimenting locally 

### Build MosaicML docker image

docker build -t gcr.io/jk-mlops-dev/mosaicml-sandbox .


### Convert C4 dataset to StreamingDataset format

```
docker run -it --gpus all --rm \
-v /home/jarekk/datasets/mosaic-c4:/mosaic-c4 \
--entrypoint /composer-python/python gcr.io/jk-mlops-dev/mosaicml-sandbox \
scripts/data_prep/convert_dataset_hf.py \
--dataset c4 --data_subset en \
--out_root /mosaic-c4 --splits train_small val_small \
--concat_tokens 2048 --tokenizer EleutherAI/gpt-neox-20b --eos_text '<|endoftext|>'
```

### Train an MPT-125m model for 10 batches

RUN_ID="run-$(date +%s)"
docker run -it --gpus all --rm --shm-size=8g \
-v /home/jarekk/datasets/mosaic-c4:/mosaic-c4 \
-v /home/jarekk/checkpoints:/checkpoints \
--entrypoint composer gcr.io/jk-mlops-dev/mosaicml-sandbox \
scripts/train/train.py \
scripts/train/yamls/pretrain/mpt-125m.yaml \
data_local=/mosaic-c4 \
train_loader.dataset.split=train_small \
eval_loader.dataset.split=val_small \
max_duration=60ba \
eval_interval=0 \
save_folder=/checkpoints/$RUN_ID


## Running jobs on Vertex persistance resource



