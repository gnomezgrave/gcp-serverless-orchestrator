from google.cloud import monitoring_v3
import time

import logging
logging.getLogger().setLevel(logging.DEBUG)

aggregation_period_seconds = 3600
fetch_interval_seconds = 43200


def get_output_element_count(project_name, job_name):
    """
    This function extracts the count of elements in the output PCollection to Kafka using the metrics client
    Using the metrics API we fetch the time-series data for the last 12 hours.
    The element count in the final PCollection is aggregated(Max value) and returned to the caller
    """
    try:
        if job_name:
            client = monitoring_v3.MetricServiceClient()
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10 ** 9)
            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": seconds, "nanos": nanos},
                    "start_time": {"seconds": (seconds - fetch_interval_seconds), "nanos": nanos},
                }
            )
            aggregation = monitoring_v3.Aggregation(
                {
                    "alignment_period": {"seconds": aggregation_period_seconds},
                    "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MAX,
                }
            )

            streamer_input = client.list_time_series(
                request={
                    "name": f'projects/{project_name}',
                    "filter": f'metric.type = "dataflow.googleapis.com/job/element_count" AND resource.labels.job_name = "{job_name}"\
                        AND metric.labels.pcollection = "Input/Read.out0"',
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    "aggregation": aggregation,
                }
            )

            records = None
            for result in streamer_input:
                records = result.points[0].value.int64_value
            
            return records
        else:
            return None
    except Exception as e:
        logging.info(f"Error occurred in fetching metrics: {e}")
        return None