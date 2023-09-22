
# Running MosaicML training workloads on Vertex AI Training persistance resources

This sample demonstrates how run MosaicML llm_foundry workloads on a Vertex AI [persitent resource](https://cloud.google.com/vertex-ai/docs/training/persistent-resource-overview). You will run jobs that pretrain MosaicML MPT models on C4 dataset.

## Developing and testing a custom training container 

In this sample we are going to use a custom training container image that packages **MosaicLM llm_foundry**.

Before submitting Vertex Training jobs it is recommended to prepare and test a docker image that will be used with Vertex AI training using a local development environment. For example you could use a user-managed instance of Vertex Workbench. Make sure that your instance has the same GPU type as the nodes in a persistance cluster. 

### Build MosaicML docker image

You will use the same docker image for both local testing and Vertex Training jobs.

```
PROJECT_ID=jk-mlops-dev
IMAGE_NAME=mosaicml-sandbox

docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME .
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME
```


### Prepare training datasets

MosaicML recommends using data in their highly efficient StreamingDataset format.

#### Convert C4 dataset to StreamingDataset format

We will use the `convert_dataset_hf.py` script to convert the HF c4 dataset to the Mosaic StreamingDataset format and push the converted dataset to Google Cloud Storage. 

##### Create a GCS bucket

Create a GCS bucket in the same region where your persistant cluster will run.

```
export REGION=asia-southeast1
export BUCKET_NAME=gs://jk-asia-southeast1-staging

gsutil mb -l $REGION $BUCKET_NAME 
```

##### Run the conversion script

export C4_GCS_LOCATION=$BUCKET_NAME/c4

docker run -it --gpus all --rm \
--entrypoint /composer-python/python gcr.io/jk-mlops-dev/mosaicml-sandbox \
scripts/data_prep/convert_dataset_hf.py \
--dataset c4 --data_subset en \
--out_root $C4_GCS_LOCATION --splits train_small val_small \
--concat_tokens 2048 --tokenizer EleutherAI/gpt-neox-20b --eos_text '<|endoftext|>'

### Test the training script


```
RUN_ID="run-$(date +%s)"

docker run -it --gpus all --rm --shm-size=8g \
-v /home/jarekk/mds_cache:/mds_cache \
-v /home/jarekk/mosaic_runs:/runs \
--entrypoint composer gcr.io/jk-mlops-dev/mosaicml-sandbox \
scripts/train/train.py \
scripts/train/yamls/pretrain/mpt-125m.yaml \
run_name=$RUN_ID \
data_local=/mds_cache  \
data_remote=$C4_GCS_LOCATION  \
train_loader.dataset.split=train_small \
eval_loader.dataset.split=val_small \
max_duration=20ba \
eval_interval=10ba \
save_folder=/runs/checkpoints/{run_name} \
loggers.tensorboard='{log_dir: /runs/logs}'

```

## Running jobs on Vertex persistance resource

### Create a persistent resource

```
REGION=asia-southeast1
PROJECT_ID=jk-mlops-dev
PERSISTENT_RESOURCE_ID=jk-a100-cluster-2
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
--enable-custom-service-account \
--resource-pool-spec="replica-count=$REPLICA_COUNT,machine-type=$MACHINE_TYPE,accelerator-type=$ACCELERATOR_TYPE,accelerator-count=$ACCELERATOR_COUNT,disk-type=$BOOT_DISK_TYPE,disk-size=$BOOT_DISK_SIZE_GB"

```

### List persistent resources

```
gcloud beta ai persistent-resources list --region=$REGION --project=$PROJECT_ID
```


### Create a Vertex Tensorboard instance


```
TENSORBOARD_NAME=jk-mosaicml-mpt-training

gcloud ai tensorboards create \
--display-name $TENSORBOARD_NAME \
--project $PROJECT_ID \
--region $REGION

```


### Create a service account for training jobs

It is highly recommended to run training jobs using a dedicated service account.

```
TRAINING_SA_NAME=vertex-training-sa

gcloud  iam service-accounts create $TRAINING_SA_NAME --project=$PROJECT_ID
```


### Grant the service account the required roles

```
SA_EMAIL="$TRAINING_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
   --member="serviceAccount:${SA_EMAIL}" \
   --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
   --member="serviceAccount:${SA_EMAIL}" \
   --role="roles/aiplatform.user"
```

### Run a job on a persistent resource

#### Configure a job spec.

We will first run a job to train a 350M MPT model. The job specification is defined the `jobspec-350m.yaml` file.

The file needs to be edited before each job is submitted:
- `containerSpec.args.run_name` - needs to be set to a unique run name for each job. This field is used to designate a name of a GCS subfolder where the artifacts created by a job will be stored
- `baseOutputDirectory.outputUriPrefix` - points to a GCS path where Vertex will assume artifacts created by a job are stored. For example Vertex will try to upload Tensorboard logs from the `logs` folder in this location. The last part of this path should be the same as a value of `containerSpec.args.run_name`
- `loggers.tensorboard` - defines a location where MosaicML will save logs. The `log_dir` key must be set to `<baseOutputDirectory.outputUriPrefix>/logs`.
- `save_folder` defines a GCS path where MosaicML saves checkpoints. This value should be set to `<baseOutputDirectory.outputUriPrefix>/checkpoints` 
- `serviceAccount` - set to your service account email
- `tensorboard` - set to a fully qualified name of your Tensorboard instance

You can get a fully qualified name of your Tensorboard instance by executing this command.

```
gcloud ai tensorboards list --project $PROJECT_ID --region $REGION --filter="displayName=$TENSORBOARD_NAME"

```

#### Submit a job

```
VERTEX_JOB_NAME="mosaicml-job-$(date +%s)"

gcloud beta ai custom-jobs create \
--region=$REGION \
--display-name=$VERTEX_JOB_NAME \
--persistent-resource-id $PERSISTENT_RESOURCE_ID \
--config=jobspec-350m.yaml
```


#### Monitor the status of the job

You can monitor the status of the job using GCP Console or using the following gcloud command:

```
gcloud beta ai custom-jobs describe <YOUR JOB ID>
```


#### Inspect the logs

You can inspect the logs using GCP Console or stream them using the following gcloud command:

```
gcloud beta ai custom-jobs stream-logs <YOUR JOB I\D>
```

#### Inspect the persistent cluster

```
gcloud beta ai persistent-resources describe $PERSISTENT_RESOURCE_ID --region $REGION --project $PROJECT_ID
```

Notice that the `usedReplicaCount` is set to 1, meaning that one of the nodes is occupied by your job.

### Submit another job

If there are available nodes on your cluster you can submit another job. In this example we will submit a job to train a 1B MPT model. The job spec is in `jobspec-1b.yaml`. Make sure to modify the job spec as described above.

```
VERTEX_JOB_NAME="mosaicml-job-$(date +%s)"

gcloud beta ai custom-jobs create \
--region=$REGION \
--display-name=$VERTEX_JOB_NAME \
--persistent-resource-id $PERSISTENT_RESOURCE_ID \
--config=jobspec-1b.yaml
```

### Inspect the artifacts created by the jobs

As configured in the job spec yaml files both the checkpoints and Tensorboard logs generated by the job are stored in the specified GCS locations.

Checkpoints are stored in the `save_model` location.
Tensorboard logs are stored in the `log_dir` location.

You can inspect these artifacts with the `gsutil` command.



### Delete a persistent resource

```
gcloud beta ai persistent-resources delete $PERSISTENT_RESOURCE_ID --region $REGION --project $PROJECT_ID
```


