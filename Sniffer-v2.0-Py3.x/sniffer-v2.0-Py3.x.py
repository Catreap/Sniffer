#encoding: utf8
import traceback
import sys
import re
import time
from Toolbox.EnvirTools import *

if not CheckEnvir(): sys.exit(1)

from Toolbox.ColorTools import *
from Toolbox.FileTools import *
from Toolbox.IfaceTools import *
from scapy.all import *
from scapy.utils import PcapWriter
from scapy.layers import http


class Sniffer:
    AllPackages = 0
    RequestPackages = 0
    CookiePackages = 0
    PostPackages = 0

    pic = '''
[1m[36m     _______..__   __. [0m[1m[31m __ [0m [1m[36m _______  _______  _______ .______      [0m
[1m[36m    /       ||  \ |  | [0m[1m[31m|  |[0m [1m[36m|   ____||   ____||   ____||   _  \     Py3.x[0m
[1m[36m   |   (----`|   \|  | [0m[1m[31m|  |[0m [1m[36m|  |__   |  |__   |  |__   |  |_)  |    [0m
[1m[36m    \   \    |  . `  | [0m[1m[31m|  |[0m [1m[36m|   __|  |   __|  |   __|  |      /     [0m
[1m[36m.----)   |   |  |\   | [0m[1m[31m|  |[0m [1m[36m|  |     |  |     |  |____ |  |\  \----.[0m
[1m[36m|_______/    |__| \__| [0m[1m[31m|__|[0m [1m[36m|__|     |__|     |_______|| _| `._____|[0m [1m[33mv2.0[0m
'''
    print(pic)

    def __init__(self,
                 iface = '',
                 newiface = 'mon0',
                 filename = '',
                 outputmode = 1,
                 savingPkt = 0,
                 savingPcap = 0,
                 filtermode = '',
                 iHost = []):

        self.iface = iface #old interface 
        self.newiface = newiface #a new interface in monitor mode
        self.sign = ['—','\\' ,'|' ,'/'] #stupid thing :)
        self.filename = filename #local pcap filename
        self.sfilename = str(int(time.time()))
        self.outputmode = outputmode #0->don't output, 1->output
        self.savingPkt = savingPkt #0->don't save, 1->save
        self.savingPcap = savingPcap
        self.filtermode = '( tcp[13:1]==24 )' #'tcp[13:1]==24' -> only sniff tcp
        self.iHost = iHost
        
        if filtermode: self.filtermode += ' and ( %s )' %filtermode #

        if self.savingPkt: InitPktsFile(self.sfilename)
        if savingPcap: self.pktdump = PcapWriter("./Pcaps/%s.pcap" %(self.sfilename), append=True, sync=True)

        if self.iface == '' and filename: 
            print(putColor('[!]Offline Mode!', 'green'))
            print('  [-]Filter:', putColor(self.filtermode, 'green'))
            print('  [-]', end='')
            ClearLine() 
            pkt = sniff(offline = './Pcaps/' + filename,    
                        prn = self.Collector,    
                        filter = self.filtermode,   
                        store = 0)#DO NOT USING store = 1!!!              
                                  #Or you'll see your memory BOOM
            print()

        else: self.Init()

        self.Exit()

    def Init(self):
        print('[!]' + putColor('Online Mode!', 'green'))

        if self.iface == '' :
            print('  [-]Auto Setting Interface...')
            self.iface = getInterface()

        ip = getLocalIP(self.iface)
        #filter the local ip	    
        self.filtermode += ' and ( ' + 'ip src not ' + ip + ' and ip dst not ' + ip + ' )'

        print('  [-]Using interface:', putColor(self.iface, 'green'))
        print('  [-]Local Ip:', putColor(ip, 'green'))
        print('  [-]Add new interface in monitor mode, named:', putColor(self.newiface, 'green'))
        StartIface(self.iface, self.newiface)

        print('[+]%s...' %putColor('Sniffing', 'green'))
        print('  [-]Filter:', putColor(self.filtermode, 'green'))
        
        try:
            sniff(iface = self.newiface, 
                  prn = self.Collector, 
                  filter = self.filtermode,
                  store = 0) #DO NOT USING store = 1!!!
                             #Or you'll see your memory BOOM
            print()

        except Exception as e:
            if 'permitted' in str(e): 
                print('[x]' + putColor('Run as root', 'red'))
            else: 
                print('\r', ' '*150)
                ErrorDog(self.Exit)         
        
    def Collector(self, pkt):
        try: 
            if self.savingPcap: 
                self.pktdump.write(pkt)
            
            self.AllPackages += 1
            if pkt.haslayer(http.HTTPRequest): 
                self.FoundRequest(pkt)

            print('\r  [%s]' %self.sign[self.AllPackages%4] + putColor(
                'AllPackages %d' %self.AllPackages, 'white'), '  ' + putColor(
                    'RequestPackages %d' %self.RequestPackages, 'blue'), '  ' + putColor(
                        'CookiePackages %d' %self.CookiePackages,'cyan'), '  ' + putColor(
                            'PostPackages %d' %self.PostPackages, 'yellow'), '  ', end='')

            ClearLine()

        except Exception as e:
            if 'ascii' not in str(e):
                ErrorDog(self.Exit)               


    def FoundRequest(self, pkt):
        if self.Plugin(pkt, 'fhost') == False: return 
        self.RequestPackages += 1
        if pkt.Cookie: self.FoundCookie(pkt)
        if pkt.Method == 'POST': self.FoundPost(pkt)


    def FoundCookie(self, pkt):
        self.CookiePackages += 1
        self.ExtractInfo(pkt, 'Cookie')

    def FoundPost(self, pkt):
        try:
            if pkt.load != None:
                self.PostPackages += 1
                self.ExtractInfo(pkt, 'Post')

        except Exception as e: 
            e = str(e)
            if 'load' not in e:
                self.PostPackages -= 1

                if 'byte' not in e: 
                    ErrorDog(self.Exit)         


    def ExtractInfo(self, pkt, method):
        if method == 'Cookie': colormethod = 'green'
        else: colormethod = 'cyan'        
        info = ['[%s]Found %s' %(putColor(time.strftime("%H:%M:%S", time.localtime()), 'white'), putColor(method, colormethod))]
        info.append('[+]From %s to %s' %(putColor(pkt.src, 'blue'), pkt.dst))
        info.append('  [-]Method: %s' %pkt.Method.decode('utf8'))
        
        try:
            ua = re.findall(r'(User-Agent: [^\\]+)', str(pkt.payload)) #fix
            info.append('  [-]%s' %ua[0])
        except Exception as e: 
            info.append('  [-]User-Agent:')
            
        if not pkt.Host: pkt.Host = ''
        info.append('  [-]Host: %s' %putColor(pkt.Host.decode('utf8'), 'green'))
        info.append('  [-]Url: %s' %((pkt.Host + pkt.Path).decode('utf8')))
        if method == 'Post': info.append('  [-]PostDatas: %s' %putColor(pkt.load, 'yellow'))

        if pkt.Cookie == None: pkt.Cookie = '' 
        info.append('  [-]Cookie: %s' %putColor(pkt.Cookie.decode('utf8'), 'yellow'))     

        if self.savingPkt: 
            SavePkts(Eraser('\n'.join(info)+'\n'+'-'*60 + '\n'), method, self.sfilename, pkt.src, pkt.Host)

        if self.outputmode:
            print('\r' + ' '*200 + '\n' + '\n'.join(info))


    def Plugin(self, pkt, plugname):
        #Your plug-in in ./Plugin
        #Such as: mode name is PPPPPPPrint
        #Then you should use: 
        #import Plugin.PPPPPPPrint
        #           
        if plugname == 'fhost':
            flist = []
            
            if pkt.Host:
                if flist and re.search('(%s)' %')|('.join(flist), pkt.Host): 
                    return False
            
            return True


    def Exit(self):
        print('\n[!]Shutting Down...')
        if self.filename == '': 
            print('  [-]Down %s...' %self.newiface)
            print('  [-]Del %s...' %self.newiface)
            ShutdownIface(self.newiface)

        if self.savingPkt: 
            print('\n[!]Analysing data...')
            Analysis(self.sfilename, self.iHost)
            print('\n[*]The name of Pkts dirPath is: ./Pkts/%s/' %putColor(self.sfilename, 'green'))
            Abandon(self.sfilename, 'pkt')# Abandon this Pkts and Pcap?

        if self.savingPcap: 
            print('\n[*]The name of Pcap is: ./Pcaps/%s' %putColor(self.sfilename, 'green'))
            Abandon(self.sfilename, 'pcap')# Abandon this Pkts and Pcap?

        
        print('\n[!]All Done!')
        print('[*]' + putColor('Have a nice day~ :)', 'green'))



iHost = []

Sniffer(savingPkt = 1, savingPcap = 1, iHost = iHost)
#Sniffer(filename='1521159939.pcap', savingPkt = 0, iHost = iHost)
