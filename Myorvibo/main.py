#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from json import *
from orvibo import *
from bottle import get, route, run, template, response, debug, request

def listcmd():
    APP_ROOT = os.path.dirname(os.path.realpath(__file__))
    IR=APP_ROOT+'/ir'
    file=os.listdir(IR)
    list_file=[]
    for l in file:
        ext =l.split('.')[-1]
        if (ext=='ir'):
            list_file.append(l)
    return list_file


response.content_type = 'application/json'

@route('/api', method='GET')
def listing():

    if (request.params.action=='discover'):
        ip = discover()
        cmd=listcmd()
        try:
            return(dumps({'succes':True, 'ip':ip,"commands":cmd}))
        except Exception as msg:
            print (msg)
            return(dumps({'succes':False}))

    elif (request.params.action=='send'):
        if (request.params.ip):
            if(request.params.touch):
                if(request.params.touch.find(',')>0):
                    try:
                        send(ip=request.params.ip,touch=request.params.touch.split(','))
                    except Exception as msg:
                        print(msg)
                        return(dumps({'succes':False,'cmd':request.params.touch}))
                    else:
                        return(dumps({'succes':True,'cmd':request.params.touch}))
                else:
                    result=send(ip=request.params.ip,touch=request.params.touch)
                    return(dumps({'succes':result,'cmd':request.params.touch}))
        else:
            if(request.params.touch):
                if(request.params.touch.find(',')>0):
                    try:
                        send(touch=request.params.touch.split(','))
                    except Exception as msg:
                        print(msg)
                        return(dumps({'succes':False,'cmd':request.params.touch}))
                    else:
                        return(dumps({'succes':True,'cmd':request.params.touch}))
                else:
                    result=send(touch=request.params.touch)
                    return(dumps({'succes':result,'cmd':request.params.touch}))

    elif (request.params.action=='learn'):
        if (request.params.ip):
            result=learn(ip=request.params.ip,touch=request.params.touch)
        else:
            result=learn(touch=request.params.touch)
        return(dumps({'succes':result,'cmd':request.params.touch}))
try:
    print(discover())
    debug(True)
    run(host='0.0.0.0', port=9000)
except InterruptedError as msg:
    print (msg)