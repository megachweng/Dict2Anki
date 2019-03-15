import json
import os

base = os.path.abspath(os.path.dirname(__file__))
configPath = os.path.join(base, 'dummyConfig.json')


class AddonManager:
    @staticmethod
    def writeConfig(*args, **kwargs):
        with open(configPath, 'w') as fp:
            json.dump(args[1], fp)

    @staticmethod
    def getConfig(*args, **kwargs):
        with open(configPath) as fp:
            return json.load(fp)
