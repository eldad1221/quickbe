# Quick back-end

## What is Quickbe

Quickbe is a Python library that enables you to deliver quick back-end components. 
If you are a technical founder or a developer, use this package to build everything you need to launch and grow high-quality SaaS application.
Every SaaS application needs these components
* Micro-services
* Web-services or APIs
* Web-hooks receivers
* Central vault

## Why Python

It has a strong community, it is fast to learn, it has lots of tools to process and analyze data ... and data is a major key for building a good app :-)

# Web server
Develop your endpoint as functions with annotations for routing and validation.
        
    @endpoint(path='hello', validation={'name': {'type': 'string', 'required': True}})
    def say_hello(session: HttpSession):
        name = session.get_parameter('name')
        if name is None:
            name = ''
        return f'Hello {name}'

Run them using Flask or as AWS Lambda function without any changes to your code.

## Build in endpoints
* `/health` - Returns 200 if every thing is OK (e.g: `{"status":"OK","timestamp":"2022-07-25 06:18:54.214674"}`)
* `/<access_key>/set_log_level/<level>` - Set log level
* `/<access_key>/quickbe-server-info` - Get verbose info on the server (endpoints and packages)
* `/<access_key>/quickbe-server-status` - Get server status (uptime, memory utilization, request per seconds and log info)
* `/<access_key>/quickbe-server-environ` - Get all environment variables keys and values
