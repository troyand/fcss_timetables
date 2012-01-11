# -*- coding: utf-8 -*-

'''
Created on Jan 2, 2011

@author: troyan
'''
import re




class Rozklad():
    '''
    Rozklad for one document
    '''
    def __init__(self, text):
        '''
        Create Rozklad from plaintext
        '''
        self.day_names = [u'ПН', u'ВТ', u'СР', u'ЧТ', u'ПТ', u'СБ', u'НД']
        self.lesson_times = [u'8.30-9.50', u'10.00-11.20', u'11.40-13.00',
                             u'13.30-14.50', u'15.00-16.20', u'16.30-17.50',
                             u'18.00-19.20']
        self.unified_lesson_times = [u'08:30-09:50', u'10:00-11:20', u'11:40-13:00', u'13:30-14:50',
                u'15:00-16:20', u'16:30-17:50', u'18:00-19:20']
        self.__text_parts = {
                             'header': [],
                             'footer': [],
                             'day_text': {}
                             }
        self.__day_lesson_text_lines = {}
        self.__init_day_text(text)
        self.__init_lesson_text()
        self.subject_abbreviations = {}
        self.__init_subject_abbreviations()
        self.__day_lessons = {}
        self.__parse_lessons()

    def day_lessons(self):
        return self.__day_lessons

    def __init_day_text(self, text):
        '''
        Init text parts day rozklad text, header and footer
        '''
        for day in self.day_names:
            self.__text_parts['day_text'][day] = []
            self.__day_lesson_text_lines[day] = {}
        current_day = None
        lines_iterator = iter(text.splitlines())
        # read header
        for line in lines_iterator:
            if line in self.day_names:
                current_day = line
                break
            else:
                self.__text_parts['header'].append(line)
        # read the day schedule
        for line in lines_iterator:
            # The line with dean limits the schedule from the foot notes
            if u'Декан' in line:
                break
            if line in self.day_names:
                current_day = line
            else:
                self.__text_parts['day_text'][current_day].append(line)
        # read the footer
        for line in lines_iterator:
            self.__text_parts['footer'].append(line)
    
    def __init_lesson_text(self):
        '''
        Read the day-lesson-time-text mapping
        '''
        for day in self.day_names:
            current_lesson_time = None
            for line in self.__text_parts['day_text'][day]:
                if line.strip() in self.lesson_times:
                    current_lesson_time = line
                elif len(line.strip()) > 1:
                    if self.__day_lesson_text_lines[day].has_key(current_lesson_time):
                        self.__day_lesson_text_lines[day][current_lesson_time].append(line)
                    else:
                        self.__day_lesson_text_lines[day][current_lesson_time] = [line]

    
    def __init_subject_abbreviations(self):
        '''
        Init the mapping of abbreviation to full subject name
        '''
        for line in self.__text_parts['footer']:
            if len(line.strip()) > 1:
                parts = line.split(u'–')
                if len(parts) == 1: 
                    parts = line.split('-')
                subject_abbreviation = parts[0].strip()
                subject_name = u'-'.join(parts[1:]).strip()
                self.subject_abbreviations[subject_abbreviation] = subject_name
    
    def __expand_subject_and_group(self, subject_string):
        '''
        Expand subject abbreviation
        strip the ellipsis
        Return full subject name and group number
        (or 0 for lecture) in a tuple
        '''
        from difflib import get_close_matches
        subject_string = subject_string.strip()
        candidates = get_close_matches(subject_string,
                               self.subject_abbreviations.values(), 2, 0.7)
        if len(candidates) == 1:
            return (candidates[0], 0)
        if len(candidates) > 1:
            print u', '.join(candidates), subject_string
            raise Exception(u'Too many subject candidates %s' % candidates)
        candidates = get_close_matches(
                       subject_string, self.subject_abbreviations.keys())
        if len(candidates) == 1:
            subject = self.subject_abbreviations[candidates[0]]
            group = None
            try:
                group = int(subject_string[-1])
            except ValueError:
                pass
            return (subject, group)
        print u', '.join(candidates), subject_string
        return ('O_o', 9)
    
    def __parse_two_lines(self, first_line, second_line):
        '''
        Parse two lines with multiple subjects
        and return list with lessons
        '''
        lessons = []
        first_list = re.findall(u"""(\d+)-(\d+[абв]?)# building and room number
            \ *
            (.*?)# subject name
            \ *
            \(([\d\-\,]*)\ *т\.\)# weeks in parentheses""",
            first_line, re.VERBOSE) 
        second_list = re.findall(u"""(ст\.в\.|доц\.|проф\.|ас\.)[ ]?([^ ]\.[ ]?[^ ]*)
        """, second_line, re.VERBOSE)
        for first_part, second_part in zip(first_list, second_list):
            building, room, subject, weeks = first_part
            subject, group = self.__expand_subject_and_group(subject)
            position, lecturer = second_part
            lessons.append((building, room, subject,
                            group, weeks, position, lecturer))
        return lessons
                
    def __parse_lessons(self):
        '''
        Parse the separate lessons
        '''
        for day in self.day_names:
            for lesson_time in self.__day_lesson_text_lines[day].keys():
                lessons = []
                lines_to_process = self.__day_lesson_text_lines[day][lesson_time]
                while lines_to_process:
                    # number of subjects in line may be defined by week ranges
                    number_of_subjects = len(re.findall(
                                                 u'т\.\)',
                                                 lines_to_process[0]))
                    if number_of_subjects > 1:
                        lessons += self.__parse_two_lines(
                                           lines_to_process[0],
                                           lines_to_process[1])
                        lines_to_process = lines_to_process[2:]
                    else:
                        buf = ''
                        parsed = False
                        while not parsed:
                            try:
                                buf += ' ' + lines_to_process[0].strip()
                            except IndexError:
                                print u'Could not parse lesson in\n%s' % buf
                                break
                            lines_to_process = lines_to_process[1:]
                            m = re.search(u"""(\d+)-(\d+[абв]?)# building and room number with optional room letter
                            \ *
                            (.*?)# subject name
                            \ *
                            \(([\d\-\,]*)\ *т\.\)# weeks in parentheses
                            \ *
                            (ст\.в\.|доц\.|проф\.|ас\.)[ ]?([^ ]\.[ ]?[^ ]*)
                            """, buf, re.VERBOSE)
                            if m:
                                building, room, subject, weeks, position, lecturer = m.groups()
                                subject, group = self.__expand_subject_and_group(subject)
                                lessons.append((building, room, subject,
                                                group, weeks, position, lecturer)) 
                                parsed = True
                if lessons:
                    self.__day_lessons.setdefault(day, {})[lesson_time] = lessons

    def __normalize_name(self, name):
        try:
            parts = name.split('.')
            surname = parts[1].strip()
            name = parts[0]
            return '%s %s. ' % (surname, name)
        except IndexError:
            return name
    
    def __unicode__(self):
        lines = []
        for day in self.day_names:
            if self.__day_lessons.has_key(day):
                lines.append(day.center(80, u'='))
                for lesson_time in self.lesson_times:
                    if self.__day_lessons[day].has_key(lesson_time):
                        lines.append(lesson_time.replace('.',':').center(80, u'-'))
                        for lesson in self.__day_lessons[day][lesson_time]:
                            lines.append(u' ~ '.join(
                                         [unicode(i) for i in lesson]))
        lines.append(u'-' * 80)
        for abbr in self.subject_abbreviations:
            lines.append(u'%s - %s' %(abbr, self.subject_abbreviations[abbr]))
        return u'\n'.join(lines)

    def csv(self):
        table = []
        for day in self.day_names:
            if self.__day_lessons.has_key(day):
                for lesson_time in self.lesson_times:
                    if self.__day_lessons[day].has_key(lesson_time):
                        time = self.unified_lesson_times[self.lesson_times.index(lesson_time)]
                        for lesson in self.__day_lessons[day][lesson_time]:
                            building, room, subject, group, weeks, position, lecturer = lesson
                            table.append([
                                day,
                                time,
                                '%s-%s' % (building, room),
                                subject,
                                unicode(group),
                                self.__normalize_name(lecturer),
                                weeks,
                                ])
        result_lines = []
        for row in table:
            result_lines.append(','.join(
                ['"%s"' % p.replace('"', '""') for p in row]
                ))
        return '\n'.join(result_lines)


def main():
    import codecs
    import traceback, sys
    rozklad_filename = sys.argv[1]
    output_csv_filename = sys.argv[2]
    rozklad_file = codecs.open(
            rozklad_filename, 'r', 'utf-8')
    text = rozklad_file.read()
    try:
        rozklad = Rozklad(text)
        #print u'%s' % rozklad
        output_csv_file = codecs.open(
                output_csv_filename, 'w', 'utf-8')
        print >>output_csv_file, rozklad.csv()
        output_csv_file.close()
    except Exception, exc:
        print exc
        print '>'*60
        traceback.print_exc(file=sys.stdout)
        print '<'*60

    


if __name__ == '__main__':
    main()
