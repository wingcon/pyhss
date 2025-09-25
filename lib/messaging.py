from redis import Redis
import time, json, uuid, traceback

class RedisMessaging:
    """
    PyHSS Redis Message Service
    A class for sending and receiving redis messages.
    """

    def __init__(self, host: str='localhost', port: int=6379, useUnixSocket: bool=False, unixSocketPath: str='/var/run/redis/redis-server.sock'):
        if useUnixSocket:
            self.redisClient = Redis(unix_socket_path=unixSocketPath)
        else:
            self.redisClient = Redis(host=host, port=port)

    def handlePrefix(self, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common'):
        """
        Adds a prefix to the Key or Queue name, if enabled.
        Returns the same Key or Queue if not enabled.
        """
        if usePrefix:
            return f"{prefixHostname}:{prefixServiceName}:{key}"
        else:
            return key

    def sendMessage(self, queue: str, message: str, queueExpiry: int=None, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Stores a message in a given Queue (Key).
        """
        try:
            queue = self.handlePrefix(key=queue, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            self.redisClient.rpush(queue, message)
            if queueExpiry is not None:
                self.redisClient.expire(queue, queueExpiry)
            return f'{message} stored in {queue} successfully.'
        except Exception as e:
            return ''

    def sendMetric(self, serviceName: str, metricName: str, metricType: str, metricAction: str, metricValue: float, metricInflux: dict={}, metricHelp: str='', metricLabels: list=[], metricTimestamp: int=time.time_ns(), metricExpiry: int=None, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Stores a prometheus metric in a format readable by the metric service.
        """
        if not isinstance(metricValue, (int, float)):
            return 'Invalid Argument: metricValue must be a digit'
        metricValue = float(metricValue)
        prometheusMetricBody = json.dumps([{
        'serviceName': serviceName,
        'timestamp': metricTimestamp,
        'NAME': metricName,
        'TYPE': metricType,
        'HELP': metricHelp,
        'LABELS': metricLabels,
        'ACTION': metricAction,
        'VALUE': metricValue,
        'INFLUX': metricInflux,
        }
        ])

        queue = self.handlePrefix(key='metric', usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)

        try:
            self.redisClient.rpush(queue, prometheusMetricBody)
            if metricExpiry is not None:
                self.redisClient.expire(queue, metricExpiry)
            return f'Succesfully stored metric called: {metricName}, with value of: {metricType}'
        except Exception as e:
            return ''
    
    def sendLogMessage(self, serviceName: str, logLevel: str, logTimestamp: int, message: str, logExpiry: int=None, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Stores a message in a given Queue (Key).
        """
        try:
            queue = self.handlePrefix(key='log', usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            logMessage = json.dumps({"message": message, "service": serviceName, "level": logLevel, "timestamp": logTimestamp})
            self.redisClient.rpush(queue, logMessage)
            if logExpiry is not None:
                self.redisClient.expire(queue, logExpiry)
            return f'{message} stored in {queue} successfully.'
        except Exception as e:
            return ''

    def getMessage(self, queue: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Gets the oldest message from a given Queue (Key), while removing it from the key as well. Deletes the key if the last message is being removed.
        """
        try:
            queue = self.handlePrefix(key=queue, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            message = self.redisClient.lpop(queue)
            if message is None:
                message = ''
            else:
                try:
                    message = message.decode()
                except (UnicodeDecodeError, AttributeError):
                    pass
            return message
        except Exception as e:
            return ''

    def getQueues(self, pattern: str='*', usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> list:
        """
        Returns all Queues (Keys) in the database.
        """
        try:
            pattern = self.handlePrefix(key=pattern, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            allQueues = self.redisClient.scan_iter(match=pattern)
            return [x.decode() for x in allQueues]
        except Exception as e:
            return f"{traceback.format_exc()}"

    def getNextQueue(self, pattern: str='*', usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> dict:
        """
        Returns the next Queue (Key) in the list.
        """
        try:
            pattern = self.handlePrefix(key=pattern, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            for nextQueue in self.redisClient.scan_iter(match=pattern):
                return nextQueue.decode()
        except Exception as e:
            return {}

    def awaitMessage(self, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common'):
        """
        Blocks until a message is received at the given key, then returns the message.
        """
        try:
            key = self.handlePrefix(key=key, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            message =  self.redisClient.blpop(key)
            return tuple(data.decode() for data in message)
        except Exception as e:
            return ''

    def awaitBulkMessage(self, key: str, count: int=100, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common'):
        """
        Blocks until one or more messages are received at the given key, then returns the amount of messages specified by count.
        """
        try:
            key = self.handlePrefix(key=key, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            message =  self.redisClient.blmpop(0, 1, key, direction='RIGHT', count=count)
            return message
        except Exception as e:
            print(traceback.format_exc())
            return ''

    def deleteQueue(self, queue: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> bool:
        """
        Deletes the given Queue (Key)
        """
        try:
            queue = self.handlePrefix(key=queue, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            self.redisClient.delete(queue)
            return True
        except Exception as e:
            return False

    def setValue(self, key: str, value: str, keyExpiry: int=None, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Stores a value under a given key and sets an expiry (in seconds) if provided.
        """
        try:
            key = self.handlePrefix(key=key, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            self.redisClient.set(key, value)
            if keyExpiry is not None:
                self.redisClient.expire(key, keyExpiry)
            return f'{value} stored in {key} successfully.'
        except Exception as e:
            return ''

    def getValue(self, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Gets the value stored under a given key.
        """
        try:
            key = self.handlePrefix(key=key, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            message = self.redisClient.get(key)
            if message is None:
                message = ''
            else:
                return message
        except Exception as e:
            return ''

    def getList(self, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> list:
        """
        Gets the list stored under a given key.
        """
        try:
            key = self.handlePrefix(key=key, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            allResults = self.redisClient.lrange(key, 0, -1)
            if allResults is None:
                result = []
            else:
                return [result.decode() for result in allResults]
        except Exception as e:
            return []

    def RedisHGetAll(self, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common'):
        """
        Wrapper for Redis HGETALL
        *Deprecated: will be removed upon completed database cleanup.
        """
        try:
            key = self.handlePrefix(key=key, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            data = self.redisClient.hgetall(key)
            return data
        except Exception as e:
            return ''
        
    def getAllHashData(self, name: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Gets all keys and values stored under a given hash.
        """
        try:
            name = self.handlePrefix(key=name, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            message = self.redisClient.hgetall(name=name)
            if message is None:
                message = ''
            else:
                decodedMessage = {}
                for key, value in message.items():
                    decodedKey = key.decode('utf-8')
                    try:
                        decodedValue = json.loads(value.decode('utf-8'))
                    except json.JSONDecodeError:
                        decodedValue = value.decode('utf-8')
                    decodedMessage[decodedKey] = decodedValue
            return decodedMessage
        except Exception as e:
            return ''

    def getHashValue(self, name: str, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Gets the value stored under a given named hash key asynchronously.
        """
        try:
            name = self.handlePrefix(key=name, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            message = self.redisClient.hget(name=name, key=key)
            if message is None:
                message = ''
            else:
                return message
        except Exception as e:
            return ''

    def setHashValue(self, name: str, key: str, value: str, keyExpiry: int=None, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Gets the value stored under a given named hash key asynchronously.
        """
        try:
            name = self.handlePrefix(key=name, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            self.redisClient.hset(name=name, key=key, value=value)
            if keyExpiry is not None:
                self.redisClient.expire(key, int(keyExpiry))
            return f'{value} stored in {key} successfully.'
        except Exception as e:
            return e

    def deleteHashKey(self, name: str, key: str, usePrefix: bool=False, prefixHostname: str='unknown', prefixServiceName: str='common') -> str:
        """
        Deletes a key: value pair stored under a hash in redis.
        """
        try:
            name = self.handlePrefix(key=name, usePrefix=usePrefix, prefixHostname=prefixHostname, prefixServiceName=prefixServiceName)
            self.redisClient.hdel(name, key)
            return f'Deleted {key} from {name} successfully.'
        except Exception as e:
            return e

if __name__ == '__main__':
    redisMessaging = RedisMessaging()
    print(redisMessaging.getNextQueue())