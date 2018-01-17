# HDM Fan Simulation Model
# Author: Kam Kwok, 2014
# Other files: hdm_data1.txt: 'person location', hdm_probes.txt: 'person in location'
# output format: exp record format (csv): probe,rt,fp,fin,fl,date,probe; file: Fresults.csv
''' FanTest 1) provides a UI, 2) creates the model as a child process, 3) env-to-model commn: set run conditions,
provides child process commands to signal task done. FanModel is the complex fan act-r model.
'''
import ccm
from ccm.lib.actr import *
import CFlib
import time
from ccm.lib.actr.hdm import *
#****************
# Utilities
#****************

class FanModel(ACTR):
    focus=Buffer()
    retrieval=Buffer()
    memory=HDM(retrieval,latency=0.63,verbose=False,N=256)
    def LoadFile(self, fn='hdm_data1.txt'): 
        try:
            datalist=[data.strip() for data in open(fn,'r').readlines()]
            for r in datalist:
                self.memory.add(r)
        except:
            print "Can't open file."
            self.stop()

    def init():
        self.LoadFile()
        print "memory loaded..."
        focus.set('wait')
    
    def wait(focus='wait',top='person:?person!None location:?location!None'):
        focus.set('test ?person ?location')
        retrieval.clear()

    def start(focus='test ?person ?location'):
        focus.set('query ?person ?location')

    def resonate(focus='query ?person ?location'):
        memory.resonance('?person ?location')
        focus.set('recall ?person ?location')

    def respond_yes(focus='recall ?person ?location',
                  retrieval='?person ?location'):
        top.sayYes()
        retrieval.clear()
        focus.set('wait')

    def respond_no(focus='recall ?person ?location',
                 retrieval=None, memory='error:True'):
        top.sayNo()
        focus.set('wait')

# the experiment
class FanTest(ccm.Model):
    def start(self):
        global fd
        # Experiment records
        exprecs=[]
        modelist=[]
        trials=0
        xlist=[]
        rtlist=[]
        for item in probes:
            value=None
            t1=self.now()
            # visual perception time:
            yield 0.47

            self.person,self.location=item.split()[0],item.split()[2]
            yield self.sayYes,self.sayNo
            self.person=None
            self.location=None

            # motor time
            yield 0.21
            rt=self.now()-t1
            value=rt
            trials=trials+1
            try:
                # fano
                fano = wd[item.split()[0]]
            except:
                fano = '1'
                # fanIn
            try:
                fanin = wd[item.split()[1]]
            except:
                fanin ='1'
                # fanl
            try:
                fanl = wd[item.split()[2]]
            except:
                fanl='1'
            # log answers
            if app.logstatus.get():
                log.CFRT[item,str(rt)]=value
            # each trial: for no error
            if ans:
                # for plotting
                xlist.append(fano+fanl)
                rtlist.append(value)
                                   
                # exp record format (csv): probe,rt,fo,fin,fl,date,probe#
                # exprecs is a list of list
                frmt_rec=[]
                # probe
                frmt_rec.append(item)
                # RT
                frmt_rec.append(rt)
                try:
                    # fano
                    frmt_rec.append(wd[item.split()[0]])
                except:
                    frmt_rec.append('1')
                    # fanIn
                try:
                    frmt_rec.append(wd[item.split()[1]])
                except:
                    frmt_rec.append('1')
                    # fanl
                try:
                    frmt_rec.append(wd[item.split()[2]])
                except:
                    frmt_rec.append('1')
                # date
                frmt_rec.append(time.ctime())
                # id
                frmt_rec.append('probe '+str(trials))
                exprecs.append(frmt_rec)
            
        
        # options for the experiment
        if app.logf.get():
            lf='Fresults.csv'
            self.fwll2csv(exprecs,lf)
        #plotxy(x_in,y_in,sym = 'ro', xl='Total Fan',
        #yl='RT (sec.)',tl='CF Experiment',fn='CFRT.png',grid=True, ll='RT (sec.)')    
        if app.plot.get():
            CFlib.plotxy(xlist,rtlist)

    def sayYes(self):
        global yescount, ans
        yescount = yescount+ 1
        ans=True

    def sayNo(self):
        global nocount, ans
        nocount = nocount+ 1
        ans=False

        
    # 1)write a list to a csv file
    def fwl2csv(self,ilist,ofn):
        ''' input: ilist = [1,2,a,b] and out-file name, output: a csv file'''
        wf = open (ofn,'a')
        for item in ilist:
            if  isinstance(item,str):
                wf.write(item+',')
            else:
                wf.write(str(item)+',')
        wf.write('\n')
        wf.close()

    # 2)write a list of lists to a csv file using fwl2csv
    def fwll2csv(self,ilist,ofn):
        for item in ilist:
            self.fwl2csv(item,ofn)

# used by: App.run_exp
def run_trial():
    #root.update()
    global nocount, yescount
    print 'No. of subjects: ',app.s_n.get()
    for t in range(1, app.s_n.get()+1):
        nocount, yescount=0.0,0.0
        env=FanTest()
        env.model=FanModel()
        env.run()
        print 'yes: ',yescount,'no: ',nocount,'error%: ',(nocount/(nocount+yescount))*100

    
#GUI and Main   
from Tkinter import *
           
class App:
    def __init__(self, master):
        frame = Frame(master)
        frame.pack()
        self.plot = IntVar(value = 0)
        self.opt_plot = Checkbutton(frame, text = "Plot RTs", variable=self.plot)
        self.opt_plot.pack(side=RIGHT)
        self.logf = IntVar(value = 0)
        self.opt_logf = Checkbutton(frame, text = "Save csv file", variable=self.logf)
        self.opt_logf.pack(side=RIGHT)
        self.logstatus = IntVar(value = 1)
        self.opt_logstatus = Checkbutton(frame, text = "Log trials", variable=self.logstatus)
        self.opt_logstatus.pack(side=RIGHT)
        self.s_n = IntVar(value = 1)
        self.ss_n = Scale(frame, label = 'No. of subjects:', variable=self.s_n,
                           from_=1, to=50, tickinterval=24, orient='horizontal')
        self.ss_n.pack(side=RIGHT)
        self.b_run = Button(frame, text="Run Experiment", fg='red',command=self.run_exp) 
        self.b_run.pack(side=LEFT)
# This is a handler for the run button - running the experiment
    def run_exp(self):
        run_trial()

# experiment init
ans=True
log=ccm.log()
fd={}

try:
    probes =[l.strip() for l in open('hdm_probes.txt','r').readlines()]
except:
    print 'No probe file!'

wd = CFlib.f2wd('hdm_probes.txt')
#fd is the fan dictionary: 'obj in loc':[fo,fc,fl]
for line in open('hdm_probes.txt','r').readlines():
    fd =CFlib.line2fdict(line.strip(),wd)

root = Tk(className=" HDM Fan Experiment")
app = App(root)
root.mainloop()
