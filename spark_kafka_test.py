from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = (
    SparkSession.builder
    .appName("FootballKafkaTest")
    .getOrCreate()
)

df = (
    spark.read
    .format("kafka")
    .option("kafka.bootstrap.servers", "football-kafka:29092")
    .option("subscribe", "football-events")
    .option("startingOffsets", "earliest")
    .option("endingOffsets", "latest")
    .load()
)

messages = df.select(
    col("topic"),
    col("partition"),
    col("offset"),
    col("value").cast("string").alias("event_json")
)

messages.show(truncate=False)

spark.stop()
