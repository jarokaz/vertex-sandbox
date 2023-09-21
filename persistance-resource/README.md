
# Running MosaicML training workloads on Vertex AI Training Persistent Resource

## Experimenting locally 

You can prepare and test a docker image that will be used with Vertex AI Training persistence resource on a user instance of Vertex Workbench. Make sure that your instance has the same GPU type as the persistance cluster. If you want to test FSDP locally allocate two GPUs to your instance.

### Build MosaicML docker image

Use the same docker image for both local testing and Vertex Training jobs.


```
docker build -t gcr.io/jk-mlops-dev/mosaicml-sandbox .
```


### Convert C4 dataset to StreamingDataset format

We will use the `convert_dataset_hf.py` script to convert the HF c4 dataset to the Mosaic StreamingDataset format and push the converted dataset to Google Cloud Storage. 

#### Create a GCS bucket

Create a GCS bucket in the same region where your persistant cluster will run.

```
export REGION=asia-southeast1
export BUCKET_NAME=gs://jk-asia-southeast1-staging

gsutil mb -l $REGION $BUCKET_NAME 
```

#### Run the conversion script

export C4_GCS_LOCATION=$BUCKET_NAME/c4

docker run -it --gpus all --rm \
--entrypoint /composer-python/python gcr.io/jk-mlops-dev/mosaicml-sandbox \
scripts/data_prep/convert_dataset_hf.py \
--dataset c4 --data_subset en \
--out_root $C4_GCS_LOCATION --splits train_small val_small \
--concat_tokens 2048 --tokenizer EleutherAI/gpt-neox-20b --eos_text '<|endoftext|>'

### Test a training run locally

MosaicML composer does not seem to properly use Google Cloud Application Default Credentials. 
For now we will save a checkpoint locally. When we run the job on a persistent cluster we will use GCSFuse to mitigate.

```
RUN_ID="run-$(date +%s)"

docker run -it --gpus all --rm --shm-size=8g \
-v /home/jarekk/mds_cache:/mds_cache \
-v /home/jarekk/checkpoints:/checkpoints \
--entrypoint composer gcr.io/jk-mlops-dev/mosaicml-sandbox \
scripts/train/train.py \
scripts/train/yamls/pretrain/mpt-125m.yaml \
data_local=/mds_cache  \
data_remote=$C4_GCS_LOCATION  \
train_loader.dataset.split=train_small \
eval_loader.dataset.split=val_small \
max_duration=20ba \
eval_interval=10ba \
save_folder=/checkpoints/$RUN_ID

```

## Running jobs on Vertex persistance resource

### Create a persistent resource

```
REGION=asia-southeast1
PROJECT_ID=jk-mlops-dev
PERSISTENT_RESOURCE_ID=jk-a100-cluster
DISPLAY_NAME=jk-a100-cluster
MACHINE_TYPE=a2-highgpu-2g
ACCELERATOR_TYPE=NVIDIA_TESLA_A100
ACCELERATOR_COUNT=2
REPLICA_COUNT=2
BOOT_DISK_TYPE=pd-ssd
BOOT_DISK_SIZE_GB=1000


gcloud beta ai persistent-resources create \
--persistent-resource-id=$PERSISTENT_RESOURCE_ID \
--display-name=$DISPLAY_NAME \
--project=$PROJECT_ID \
--region=$REGION \
--resource-pool-spec="replica-count=$REPLICA_COUNT,machine-type=$MACHINE_TYPE,accelerator-type=$ACCELERATOR_TYPE,accelerator-count=$ACCELERATOR_COUNT,disk-type=$BOOT_DISK_TYPE,disk-size=$BOOT_DISK_SIZE_GB"

```

### List persistent resources

```
gcloud beta ai persistent-resources list --region=$REGION --project=$PROJECT_ID
```



### List persistent resources

gcloud beta ai persistent-resources list --region $REGION


### Run a job on a persistent resource

JOB_NAME="mosaicml-job-$(date +%s)"
PERSISTENT_RESOURCE_ID=jk-a100-cluster-asia

gcloud beta ai custom-jobs create \
--region=$REGION \
--display-name=$JOB_NAME \
--persistent-resource-id $PERSISTENT_RESOURCE_ID \
--config=jobspec.yaml

This command will print out the job id

### Monitor the status of the job

You can monitor the status of the job using GCP Console or using the following gcloud command:

```
gcloud beta ai custom-jobs describe <YOUR JOB ID>
```


### Inspect the logs

You can inspect the logs using GCP Console or stream them using the following gcloud command:

```
gcloud beta ai custom-jobs stream-logs <YOUR JOB I\D>
```


### Delete a persistent resource

```
gcloud beta ai persistent-resources delete $PERSISTENT_RESOURCE_ID --region $REGION --project $PROJECT_ID
```


