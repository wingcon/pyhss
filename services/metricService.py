import asyncio
import sys, os, json
import time, json, yaml
import socket
from prometheus_client import make_wsgi_app, start_http_server, Counter, Gauge, Summary, Histogram, CollectorRegistry
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask
from influxdb import InfluxDBClient
import threading
import traceback
sys.path.append(os.path.realpath('../lib'))
from messaging import RedisMessaging
from banners import Banners
from logtool import LogTool

class MetricService:

    def __init__(self, redisHost: str='127.0.0.1', redisPort: int=6379):
        try:
            with open("../config.yaml", "r") as self.configFile:
                self.config = yaml.safe_load(self.configFile)
        except:
            print(f"[Metric] Fatal Error - config.yaml not found, exiting.")
            quit()
    
        self.redisMessaging = RedisMessaging(host=redisHost, port=redisPort)
        self.banners = Banners()
        self.logTool = LogTool(config=self.config)
        self.registry = CollectorRegistry(auto_describe=True)
        self.logTool.log(service='Metric', level='info', message=f"{self.banners.metricService()}", redisClient=self.redisMessaging)
        self.hostname = socket.gethostname()
        self.influxEnabled = self.config.get('influxdb', {}).get('enabled', None)
        self.influxDatabase = self.config.get('influxdb', {}).get('database', None)
        self.influxUser = self.config.get('influxdb', {}).get('username', None)
        self.influxPassword = self.config.get('influxdb', {}).get('password', None)
        self.influxHost = self.config.get('influxdb', {}).get('host', None)
        self.influxPort = self.config.get('influxdb', {}).get('port', None)

    def processInfluxdb(self, influxData: dict) -> bool:
        """
        Sends defined InfluxDB Metrics to InfluxDB, if configured.
        """

        if not self.influxEnabled:
            return True
        if not self.influxDatabase:
            return True
        if not self.influxUser:
            return True
        if not self.influxPassword:
            return True
        if not self.influxHost:
            return True
        if not self.influxPort:
            return True
    
        influxClient = InfluxDBClient(self.influxHost, self.influxPort, self.influxUser, self.influxPassword, self.influxDatabase)

        if not isinstance(influxData, list):
            influxData = [influxData]

        influxClient.write_points(influxData)
        
        return True

    
    def handleMetrics(self):
        """
        Collects queued metrics from redis, and exposes them using prometheus_client.
        """
        try:
            actions = {'inc': 'inc', 'dec': 'dec', 'set':'set'}
            prometheusTypes = {'counter': Counter, 'gauge': Gauge, 'histogram': Histogram, 'summary': Summary}

            metric = self.redisMessaging.awaitMessage(key='metric', usePrefix=True, prefixHostname=self.hostname, prefixServiceName='metric')[1]

            self.logTool.log(service='Metric', level='debug', message=f"[Metric] [handleMetrics] Received Metric: {metric}", redisClient=self.redisMessaging)
            prometheusJsonList = json.loads(metric)

            for prometheusJson in prometheusJsonList:
                self.logTool.log(service='Metric', level='debug', message=f"[Metric] [handleMetrics] {prometheusJson}", redisClient=self.redisMessaging)
                if not all(key in prometheusJson for key in ('NAME', 'TYPE', 'ACTION', 'VALUE')):
                    raise ValueError('All fields are not available for parsing')
                counterName = prometheusJson['NAME']
                counterType = prometheusTypes.get(prometheusJson['TYPE'].lower())
                counterAction = prometheusJson['ACTION'].lower()
                counterValue = float(prometheusJson['VALUE'])
                counterHelp = prometheusJson.get('HELP', '')
                counterLabels = prometheusJson.get('LABELS', {})

                try:
                    metricInflux = prometheusJson.get('INFLUX', {})
                    if metricInflux:
                        self.processInfluxdb(influxData=metricInflux)
                except Exception as e:
                    self.logTool.log(service='Metric', level='warn', message=f"[Metric] [handleMetrics] Error processing metric InfluxDb content: {traceback.format_exc()}", redisClient=self.redisMessaging)

                if isinstance(counterLabels, list):
                            counterLabels = dict()

                if counterType is not None:
                    try:
                        counterRecord = counterType(counterName, counterHelp, labelnames=counterLabels.keys(), registry=self.registry)
                        if counterLabels:
                            counterRecord = counterRecord.labels(*counterLabels.values())
                    except ValueError as e:
                        counterRecord = self.registry._names_to_collectors.get(counterName)
                        if counterLabels and counterRecord:
                            counterRecord = counterRecord.labels(*counterLabels.values())
                    action = actions.get(counterAction)
                    if action is not None:
                        prometheusMethod = getattr(counterRecord, action)
                        prometheusMethod(counterValue)
                    else:
                        self.logTool.log(service='Metric', level='warn', message=f"[Metric] [handleMetrics] Invalid action '{counterAction}' in message: {metric}, skipping.", redisClient=self.redisMessaging)
                        continue
                else:
                    self.logTool.log(service='Metric', level='warn', message=f"[Metric] [handleMetrics] Invalid type '{counterType}' in message: {metric}, skipping.", redisClient=self.redisMessaging)
                    continue

        except Exception as e:
            self.logTool.log(service='Metric', level='error', message=f"[Metric] [handleMetrics] Unable to parse message: {metric}, due to {e}. Skipping.", redisClient=self.redisMessaging)
            return


    def getMetrics(self):
        while True:
            self.handleMetrics()


if __name__ == '__main__':

    metricService = MetricService()
    metricServiceThread = threading.Thread(target=metricService.getMetrics)
    metricServiceThread.start()

    prometheusWebClient = Flask(__name__)
    prometheusWebClient.wsgi_app = DispatcherMiddleware(prometheusWebClient.wsgi_app, {
        '/metrics': make_wsgi_app(registry=metricService.registry)
    })

    prometheusWebClient.run(host='0.0.0.0', port=9191)