'''
Emotion-based melody transformation script
Alexey Kalinin, 2017

Requirements: python3, music21
              docker - for running BachBot

music21._version.__version__
'4.1.0'
pip3 install --upgrade music21

Using:
- call from console:
       python3 emotransform.py --emotion JOY input.mid
       output: transformed file JOY_input.mid

- from other python script
       from emotransform import transform
       transform('input.mid','JOY')
       output: transformed file JOY_input.mid
'''

import sys
import os
import uuid
import argparse
import music21
import subprocess
import xml.etree.ElementTree as et

EMOTIONS = (
    'ANXIETY',
    'AWE',
    'GRATITUDE',
    'JOY',
    'SADNESS',
    #'SERENITY',
    'DETERMINATION'
    )

remote_folder = '/root/bachbot/emo_src/'

def initBachBot():
    # ensure that bachbot image started
    subprocess.Popen(['docker', 'start', 'bachbot']).wait()

    # make target folder on start
    subprocess.Popen(['docker', 'exec', 'bachbot', 'mkdir', '-p', remote_folder]).wait()

# init BachBot on import
initBachBot()

def transform(filename, targetEmotion, targetDir='.'):
    ''' Perform emotion-based transformation. Output - transformed midi-file '''
    if (not os.path.exists(targetDir)): os.makedirs(targetDir)

    src_score = music21.converter.parse(filename)
    src_key = src_score.analyze('key')

    print("Source scale is", src_key.tonic.name, src_key.mode)
    print('Transforming {0} to {1}'.format(filename, targetEmotion))

    (_, filename) = os.path.split(filename)
    (filename_stripped, file_format) = filename.split('.')

    part = None

    if file_format == 'mid':
        assert len(src_score) == 1, 'Not enough parts in score'
        part = src_score[0]
    if file_format == 'xml':
        part = src_score

    currentScale = None
    if src_key.mode == 'major':
        currentScale = music21.scale.MajorScale(src_key.tonic.name)
    else:
        currentScale = music21.scale.MinorScale(src_key.tonic.name)

    # ANXIETY
    if targetEmotion == 'ANXIETY':
        notes = part.flat.getElementsByClass(music21.note.Note)
        for currNote in notes:
            currDegree = currentScale.getScaleDegreeFromPitch(currNote)
            minorsDegrees = (3, 6)
            if currDegree in minorsDegrees:  # change to minor (almost) - halftone lower III and VI degree, VII - leave untouched
                currNote.transpose(-1, inPlace=True)
                #TODO: add syncope
                #print('Beats ', currNote.offset, currNote.beat)
                #currNote.offset = currNote.offset - 0.3
                #print('Updated ', currNote)

    # SADNESS
    if targetEmotion == 'SADNESS':
        #part.scaleOffsets(2.0).scaleDurations(2.0)
        tempo = part.flat.getElementsByClass(music21.tempo.MetronomeMark)
        tempo[0].setQuarterBPM(60)

        notes = part.flat.getElementsByClass(music21.note.Note)
        for currNote in notes:
            #currNote.quarterLength = 2*currNote.quarterLength
            currDegree = currentScale.getScaleDegreeFromPitch(currNote)
            minorsDegrees = (3, 6, 7)
            if currDegree in minorsDegrees:  # completely change to minor - halftone lower III, VI and VII degree
                currNote.transpose(-1, inPlace=True)

    # AWE
    if targetEmotion == 'AWE':
        tempo = part.flat.getElementsByClass(music21.tempo.MetronomeMark)
        tempo[0].setQuarterBPM(60)
        #part.scaleOffsets(1.8, inPlace=True)
        #part.scaleDurations(1.8, inPlace=True)
        #part.augmentOrDiminish(2, inPlace=True)
        notes = part.flat.getElementsByClass(music21.note.Note)
        for currNote in notes:
            #currNote.quarterLength = 4.00
            currDegree = currentScale.getScaleDegreeFromPitch(currNote)

            # Transitions, which should be changed
            # curr   next
            #   1 -> 5
            #   1 -> 4
            #   4 -> 1
            #   5 -> 1
            transition_degrees = {
                1:[4, 5],
                4:[1],
                5:[1]
            }

            if currDegree in transition_degrees:
                #lookup for next note
                nextNote = part.flat.getElementAfterElement(currNote, [music21.note.Note])
                if nextNote == None: break

                nextNoteDegree = currentScale.getScaleDegreeFromPitch(nextNote)
                nextCheckDegrees = transition_degrees[currDegree]

                if nextNoteDegree in nextCheckDegrees:
                    #note change - connected with prev degree
                    if (currDegree == 1) and (nextNoteDegree in (4, 5)):
                        shiftInterval = music21.interval.Interval(nextNote, music21.note.Note(currentScale.pitchFromDegree(6)))
                        nextNote.transpose(shiftInterval, inPlace=True)

                    if (currDegree in (4, 5)) and (nextNoteDegree == 1):
                        shiftInterval = music21.interval.Interval(currNote, music21.note.Note(currentScale.pitchFromDegree(3)))
                        currNote.transpose(shiftInterval, inPlace=True)

    # JOY
    if targetEmotion == 'JOY':
        # pentatonic, replace 4 и 7 degree
        notes = part.flat.getElementsByClass(music21.note.Note)
        for currNote in notes:
            currDegree = currentScale.getScaleDegreeFromPitch(currNote)
            notPentaDegrees = (4, 7)
            if currDegree in notPentaDegrees:
                if currDegree == 4:
                    shiftInterval = music21.interval.Interval(currNote, music21.note.Note(currentScale.pitchFromDegree(5)))
                    currNote.transpose(shiftInterval, inPlace=True)
                if currDegree == 7:
                    shiftInterval = music21.interval.Interval(currNote, music21.note.Note(currentScale.pitchFromDegree(1)))
                    currNote.transpose(shiftInterval, inPlace=True)

    # DETERMINATION
    if targetEmotion == 'DETERMINATION':
        #TODO: translate to major if needed
        #TODO: rhythm: add syncops

        notes = part.flat.getElementsByClass(music21.note.Note)
        for currNote in notes:
            # shorten note duration, except last in each phrase
            if currNote.quarterLength <= 1:
                currNote.quarterLength = 0.5*currNote.quarterLength

    # GRATITUDE
    if targetEmotion == 'GRATITUDE':
        notes = part.flat.getElementsByClass(music21.note.Note)
        phraseFirstNote = None  # quasi first note of the phrase
        for currNote in notes:
            if currNote.beat == 1 and phraseFirstNote is None:
                phraseFirstNote = currNote

            if currNote.quarterLength >= 2:
                currNote.quarterLength = currNote.quarterLength/4 #2

                newNote = music21.note.Note(phraseFirstNote.pitch.nameWithOctave)
                newNote.quarterLength = 0.5 #0.5

                num = currNote.measureNumber
                target_measure = part.recurse().getElementsByClass(music21.stream.Measure)[num-1]
                target_measure.insert(1,newNote)
                #part.insert(currNote.offset+0.5, newNote)
                #part.insert(float(currNote.getOffsetBySite(part))+0.5, newNote)

                phraseFirstNote = None #reset first note of the phrase

    # TRANQUILITY/SERENITY
    if targetEmotion == 'SERENITY':
        assert False, 'SERENITY under construction!'

    # transpose key signature
    #for ks in src_score.flat.getKeySignatures():
    #    ks.transpose(halfSteps, inPlace=True)

    uuid_part = str(uuid.uuid1())
    file_format = 'xml'
    newFileName=filename_stripped + '_' + targetEmotion +'_' + uuid_part + '.' + file_format
    newFileNamePath = targetDir +'/' + newFileName
    src_score.write(file_format, newFileNamePath)

    return newFileName, targetDir


def nn_harmonize(filename, targetDir, targetEmotion):
    '''Perform neural network harmonization via BachBot. Output - transformed midi-file '''

    (_, filename) = os.path.split(filename)
    (filename_stripped, file_format) = filename.split('.')

    #if (file_format == 'midi'): subprocess.Popen(['musescore', filename, '-o',filename_stripped + '.xml']).wait()

    # copy file to bachbot docker instance
    subprocess.Popen(['docker', 'cp', targetDir + '/' + filename, 'bachbot:' + remote_folder + filename]).wait()

    #run BachBot harmonization
    checkpoint_folder = '/root/bachbot/scratch/checkpoints/trained_model/'
    #TODO: random select of checkpoiont (read list from bachbot docker)
    #NOTE: remote file name must be without extension - JOY.xml -> JOY , due some bash/zsh mess
    checkpoint_filename = 'checkpoint_5000.t7'
    harm_args = [
                   'docker', 'exec', '-ti', 'bachbot', 'bash',
                   '/root/bachbot/scripts/harmonize_melody.zsh',
                   remote_folder + filename_stripped,
                   checkpoint_folder + checkpoint_filename
                ]
    subprocess.Popen(harm_args).wait()

    # copy processed file back to host
    result_file_name = filename_stripped + '_harm'
    musicXML_file = targetDir + '/' + result_file_name + '.xml'
    subprocess.Popen(['docker', 'cp', 'bachbot:/root/bachbot/scratch/out/decode.xml', musicXML_file]).wait()

    # remove old decode.xml
    subprocess.Popen(['docker', 'exec', 'bachbot', 'rm', '/root/bachbot/scratch/out/decode.xml']).wait()
    # remove related files from remote_folder, * not work via docker call so remove explicitly by name
    rm_list = [
                remote_folder + filename_stripped + '-harm.utf',
                remote_folder + filename_stripped + '.utf',
                remote_folder + filename_stripped + '.xml'
              ]
    for f in rm_list: subprocess.Popen(['docker', 'exec', 'bachbot', 'rm', f])


    #patching musicXML file! -  bachBot removes midi-instrument element,
    #                           but music21 fails to properly convert to midi without it...

    tree = et.parse(musicXML_file)
    root = tree.getroot()

    midi_inst = et.fromstring('''
          <midi-instrument id="id111">
           <midi-channel>1</midi-channel>
           <midi-program>1</midi-program>
          </midi-instrument>''')

    score_part = root.find('part-list/score-part')
    score_part.insert(0, midi_inst)
    tree.write(musicXML_file, encoding='UTF-8', xml_declaration=True)


    # convert to MIDI
    midi_file = targetDir + '/' + result_file_name + '.mid'
    score = music21.converter.parse(musicXML_file)

    # insert tempo change, if transformation needed (bachbot removes it too..)
    slowed_transformations = ['AWE', 'SADNESS']
    if (targetEmotion in slowed_transformations):
        measure_for_bpm = score.recurse().getElementsByClass(music21.stream.Measure)[0]
        measure_for_bpm.insert(0, music21.tempo.MetronomeMark('', 80))

    score.write('midi', midi_file)

    #NOTE: debug convert to XML->MIDI via musescore
    #subprocess.Popen(['musescore', musicXML_file, '-o', midi_file]).wait()

    return result_file_name + '.mid', targetDir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('''2 parameters needed!\nUsage: emo-transform.py filename --emotion EMOTION  ''')
        quit()

    parser = argparse.ArgumentParser()
    parser.add_argument('--emotion', dest='emotion')
    parser.add_argument('filename', type=str)
    args = parser.parse_args()

    if (args.emotion in EMOTIONS) == False:
        print('Please, specify one of possible emotions: ', EMOTIONS)
        quit()

    newFileName, targetDir = transform(filename=args.filename, targetEmotion=args.emotion)
    nn_harmonize(newFileName, targetDir, targetEmotion=args.emotion)

