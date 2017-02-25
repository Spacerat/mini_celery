import json
import pickle
class JSONTransport():
    """ Transports specify how function arguments should be encoded/decoded """
    def encode(self, value):
        if isinstance(value, Exception):
            value = {'exception': str(value)}
            
        return json.dumps(value)
    def decode(self, encoded):
        decoded = json.loads(encoded)
        try:
            if 'exception' in decoded:
                return Exception(decoded['exception'])
        except TypeError:
            pass
        return decoded
