#################### ham cheese forgetting DM model ###################

# this model turns on the subsymbolic processing for DM, which causes forgetting


import ccm      
log=ccm.log()   

from ccm.lib.actr import *  

#####
# Python ACT-R requires an environment
# but in this case we will not be using anything in the environment
# so we 'pass' on putting things in there

class MyEnvironment(ccm.Model):
    display = ccm.Model(word="START")
    report  = [0]*20
    
    # start present the list
    def start_list(self):
        stimuli = range(1,21)
        stimuli = stimuli + ["END","RECALL"]
        for stimulus in stimuli:
            yield 1
            self.display.word = "NONE"
            yield 1
            self.display.word = stimulus
    
    # turn off the display at the end of the experiment
    def end_experiment(self):
        self.display.word = "OFF"

    def report_word(self,word):
        if word != "START":
            if word != "END":
                self.report[int(word) - 1] = self.report[int(word) - 1] + 1

#####
# create an act-r agent

class MyAgent(ACTR):
    focus=Buffer()
    auditory=Buffer()
    DMbuffer=Buffer()                   
    
    Use_HDM = False
    
    if Use_HDM: # standard latency = 0.05
        DM=HDM(DMbuffer,N=64,latency=0.5,verbose=False,noise=1.0,forgetting=0.9,finst_size=22,finst_time=100.0)
    else: # standard latency = 0.05
        DM=Memory(DMbuffer,latency=3.0,threshold=0,finst_size=22,finst_time=100.0)     
                                                     # latency controls the relationship between activation and recall
                                                     # activation must be above threshold - can be set to none
            
        dm_n=DMNoise(DM,noise=0.0,baseNoise=0.0)         # turn on for DM subsymbolic processing
        dm_bl=DMBaseLevel(DM,decay=0.5,limit=None)       # turn on for DM subsymbolic processing


    # STUDY THE LIST
    
    def init():
        self.parent.start_list()
        focus.set('phase:STUDY waiting:TRUE rehearsal:FALSE')
        auditory.set('START START')
    
    def prepare_for_word(focus='phase:STUDY waiting:FALSE rehearsal:?STATUS', display='word:NONE'):
        focus.set('phase:STUDY waiting:TRUE rehearsal:?STATUS')
    
    def notice_word(focus='phase:STUDY waiting:TRUE', display='word:!NONE!RECALL?A', auditory='?B ?C'):
        print "I notice the new word is " + A
        auditory.set('?A ?B')
        focus.set('phase:STUDY waiting:FALSE rehearsal:FALSE')

    # RECALL THE LIST, SEARCHING BACKWARD FROM THE END

    def begin_recall(focus='phase:STUDY waiting:TRUE', display='word:RECALL'):
        print "Trying to do free recall of the list."
        DM.finst.obj = []
        focus.set('phase:TEST waiting:FALSE search:REVERSE')
        auditory.set('END')

    def request(focus='phase:TEST waiting:FALSE search:REVERSE',auditory='?query'):
        print "Finst contains:" + str(DM.finst.obj)
        DM.request('?query ?',require_new=True)
        focus.set('phase:TEST waiting:TRUE search:REVERSE')

    def recall(focus='phase:TEST waiting:TRUE search:REVERSE', DMbuffer='?A !START?B', DM='busy:False'):  
        print "I remember " + B
        self.parent.report_word(B)
        auditory.set('?B')
        focus.set('phase:TEST waiting:FALSE search:REVERSE')
    
    def forgot_once(focus='phase:TEST waiting:TRUE search:REVERSE', DMbuffer=None, DM='error:True'):
        print "I forget. Let me start from the beginning."
        focus.set('phase:TEST waiting:FALSE search:FORWARD')
        auditory.set('START')
        
    def found_start(focus='phase:TEST waiting:TRUE search:REVERSE', DMbuffer='?A START'):  
        print "I'm at the start of the list. Let's search forward now."
        auditory.set('START')
        focus.set('phase:TEST waiting:FALSE search:FORWARD')
        
    # RECALL THE LIST, SEARCHING FORWARD FROM THE START

    def request_forward(focus='phase:TEST waiting:FALSE search:FORWARD',auditory='?query'):
        print "Finst contains:" + str(DM.finst.obj)
        DM.request('? ?query',require_new=True)
        focus.set('phase:TEST waiting:TRUE search:FORWARD')

    def recall_forward(focus='phase:TEST waiting:TRUE search:FORWARD', DMbuffer='!END?A !END?B', DM='busy:False'):  
        print "I remember " + A
        self.parent.report_word(A)
        auditory.set('?A')
        focus.set('phase:TEST waiting:FALSE search:FORWARD')

    def forgot_twice(focus='phase:TEST waiting:TRUE search:FORWARD', DMbuffer=None, DM='error:True'):
        print "I forgot again. I give up."
        focus.set('stop')

    def found_end(focus='phase:TEST waiting:TRUE search:FORWARD', DMbuffer='END ?A'):  
        print "I'm at the end of the list. Let's quit."
        focus.set('stop')
    
    # REHEARSE LIST DURING STUDY PHASE

    def rehearse_add(focus='phase:STUDY waiting:?STATUS rehearsal:FALSE', auditory='!START?A !START?B'):
        DM.add('?A ?B')
        DM.request('? START')
        focus.set('phase:STUDY waiting:?STATUS rehearsal:TRUE')
    
    def rehearse_retrieve(focus='phase:STUDY waiting:?STATUS rehearsal:TRUE', DMbuffer='?A ?B', DM='busy:False'):
        DM.add('?A ?B')
        DM.request('? ?A')
        focus.set('phase:STUDY waiting:?STATUS rehearsal:TRUE')
    
    def rehearse_forget(focus='phase:STUDY waiting:?STATUS rehearsal:TRUE',DMbuffer=None, DM='error:True'):
        focus.set('phase:STUDY waiting:?STATUS rehearsal:FALSE')

    def basic_rehearse(focus='phase:STUDY', auditory='?A ?B'):
        DM.add('?A ?B')

    # END EXPERIMENT
    
    def stop_production(focus='stop'):
        self.parent.end_experiment()
        self.stop()

tim=MyAgent()                              # name the agent
subway=MyEnvironment()                     # name the environment
subway.agent=tim                           # put the agent in the environment
ccm.log_everything(subway)                 # print out what happens in the environment
log=ccm.log(html=True)

times = []
activation = []
prev_stimulus = False

run_name = "_items=20_DM_l=30_run10"
#run_name = "_items=20_HDM_l=5_d=32_f=9_n=20_run8"

while subway.display.word != "OFF":
   subway.run(limit=0.1)   # run simulation for 100ms
   times.append(subway.now())
   try:
        a = subway.agent.DM.get_activation('2 1')
   except:
        a = 0.0
   activation.append(a)
   if subway.display.word == "RECALL" and (not prev_stimulus):
        print "writing curve file"
        stimuli = ['START'] + range(1,21) + ['END']
        curve_file = open('curve' + run_name + '.txt','w')
        for stimulus in stimuli:
            if prev_stimulus:
                the_chunk = str(stimulus) + ' ' + str(prev_stimulus)
                a = subway.agent.DM.get_activation(the_chunk)
                curve_file.write("%s \n" % a)
                #curve_file.write("%s %s \n" % (the_chunk, a))
            prev_stimulus = stimulus
  
# write the recalled words to a file
recall_file = open('list_recalled' + run_name + '.txt', 'w')
for word in subway.report:
    recall_file.write("%s \n" % word)

# write the activations to a file
act_file = open('list_activations' + run_name + '.txt', 'w')
for a in activation:
    act_file.write("%s \n" % a)

ccm.finished()                             # stop the environment
