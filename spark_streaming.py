from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp

spark = (
    SparkSession.builder
    .appName("FootballRealTimePipeline")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

kafka_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "football-kafka:29092")
    .option("subscribe", "football-events")
    .option("startingOffsets", "earliest")
    .load()
)

processed_stream = kafka_stream.select(
    col("key"),
    col("value"),
    current_timestamp().alias("spark_processed_at")
)

output_stream = processed_stream.select(
    col("key"),
    col("value")
)

query = (
    output_stream.writeStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "football-kafka:29092")
    .option("topic", "football-processed")
    .option("checkpointLocation", "/tmp/football-stream-checkpoint")
    .outputMode("append")
    .start()
)

print("Football Spark streaming pipeline started.")
print("football-events -> Spark -> football-processed")

query.awaitTermination()