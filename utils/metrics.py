import time


class MetricsTracker:
    def __init__(self):
        self.total_queries = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_retries = 0
        self.empty_results = 0
        self.unsafe_queries = 0
        self.intent_failures = 0
        self.total_latency = 0

    def start_timer(self):
        return time.time()

    def end_timer(self, start_time):
        self.total_latency += (time.time() - start_time)

    def log_query(self):
        self.total_queries += 1

    def log_success(self):
        self.success_count += 1

    def log_failure(self):
        self.failure_count += 1

    def log_retry(self):
        self.total_retries += 1

    def log_empty(self):
        self.empty_results += 1

    def log_unsafe(self):
        self.unsafe_queries += 1

    def log_intent_failure(self):
        self.intent_failures += 1

    def report(self):
        return {
            "total_queries": self.total_queries,
            "success_rate (%)": round(
                (self.success_count / self.total_queries) * 100, 2
            ) if self.total_queries else 0,
            "failure_rate (%)": round(
                (self.failure_count / self.total_queries) * 100, 2
            ) if self.total_queries else 0,
            "avg_retries": round(
                self.total_retries / self.total_queries, 2
            ) if self.total_queries else 0,
            "empty_result_rate (%)": round(
                (self.empty_results / self.total_queries) * 100, 2
            ) if self.total_queries else 0,
            "unsafe_query_rate (%)": round(
                (self.unsafe_queries / self.total_queries) * 100, 2
            ) if self.total_queries else 0,
            "intent_failure_rate (%)": round(
                (self.intent_failures / self.total_queries) * 100, 2
            ) if self.total_queries else 0,
            "avg_latency (s)": round(
                self.total_latency / self.total_queries, 2
            ) if self.total_queries else 0,
        }
