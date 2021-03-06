
import sys
import argparse
import re
from thread_hotfix import Thread
import time

# Helper: checks if a string is a time string
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
def contains_time(s):
    for month in months:
        if s.find(month) >= 0 and s.find("20") >= 0:
            return True
    return False

# Given a list of names, sort alpahbetically by last name.
# Assertion, names have 2+ words and "last name" is the very last word of the name.
def sort_alphabetical(l):
    l.sort(key = lambda s: s.split()[-1])
    return l

def read_path(path):
    threads = []
    contents = []
    with open(path, "r") as input:
        lines = input.readlines()

        try:
            lines.remove("100%\n")
            lines.remove("36\n")
            lines.remove("To enable screen reader support, press ⌘+Option+Z To learn about keyboard shortcuts, press ⌘slash\n")
        except ValueError:
            pass

        ## Get the case where the first name is copied fully
        ## Assert: the first line contains the name of the first comment, which must be then repeated
        ## in the next line, alone with time stamp. If this is not, then force it.
        if lines[1].find(lines[0]) < 0:
            m = re.search(r"\d", lines[0])
            if m is not None:
                start = m.start()
                start -= 4
            else:
                start = 0
            name = lines[0][:start]
            lines = [name] + lines
        
        markers = []
        lines = [x.replace("\n", "") if x.find("\n")>=0 else x for x in lines ]
        special_case = -2
        ## SELECT TEXT special case
        for i in range(len(lines)-1):
            if lines[i] == "SELECTED TEXT:":
                special_case = i
            if lines[i+1].find(lines[i]) >=0 and i != special_case+1:
                lines[i+1] = lines[i+1].replace(lines[i], "")
                if contains_time(lines[i+1]):
                    lines[i+1] = lines[i+1]
                    markers.append(i)
    markers.append(len(lines))
    # will strike if EXACT match
    strikes = ["Suggestion accepted", "Suggestion rejected", "Add space", "Made a suggestion", "Marked as resolved",\
               "Add paragraph", "Add tab", "Delete space", "Delete paragraph", "Delete tab" ]
    # will strike if INCLUDES match
    inclusion_strikes = ["Delete:", "Add:", "Replace:"]
    for i in range( len(markers)-1):
        valid = True
        entry = lines[markers[i]:markers[i+1]]
        # Marked as resolved is ok, if there is also "re-opened"
        for e in entry:
            if e in strikes:
                valid = False

            for i in inclusion_strikes:
                if e.find(i) >=0:
                    valid = False
            # Dealing with the 'marked as resolved' case. If it is re-opened, we need to toggle it back to being 'valid'
            if e == "Re-opened":
                valid = True
        if valid:
            threads.append([x for x in entry if x != ""])

    return threads

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required = True, help = "location of the file")
    parser.add_argument('--names', action = 'store_true', help = "Lists all the names of students who commented, in alphabetical order by last name")
    parser.add_argument('--stats', action = 'store_true', help = "Shows all students in alphabetical order, with number of comments and number of replies")
    parser.add_argument('--verbose', metavar = "output", type = str, help = "Shows all students in alphabetical order, with sequenced list of each reply. \
                                                                            No reply contents. Writes it to an output file.")
    parser.add_argument('--full', metavar = "output", type = str, help = "Writes to output file of the comments on the google doc, cleaned up from automated\
                                                                            messages, in the order they appear on the document")
    args = parser.parse_args()


    master = []
    threads = read_path(args.file)
    for i in range(len(threads)):
        t = Thread()
        t.process_text(threads[i])
        master.append(t)

    # Debug
    for thread in master:
        names = thread.get_users()
        comms = thread.get_comments()
    if args.names:
        names = []
        for thread in master:
            names = names + thread.get_users()
        names = list(set(names))
        print("Total " + str(len(names)) + " unique participants")
        print(sort_alphabetical(names))

    elif args.stats:
        names  = []
        for thread in master:
            names = names + thread.get_users()
        names = list(set(names))
        names = sort_alphabetical(names)
        comments = [0] * len(names)
        replies = [0] * len(names)
        # Loop through threads
        for thread in master:
            users = thread.get_users()
            for i in range(len(users)):
                if i == 0:
                    loc = names.index(users[i])
                    comments[loc] = comments[loc] + 1
                else:
                    loc = names.index(users[i])
                    replies[loc] = replies[loc] + 1
        print("Statistics of all students, with number of comments and replies.")
        print ('%-40s%-30s%-30s' % ("Name", "Number of Comments", "Number of Replies"))

        for i in range(len(names)):
            print ('%-40s%-30i%-30i' % (str(names[i]), comments[i], replies[i]))

    elif args.verbose:
        writer = open(args.verbose, "w")
        writer.write("List of all timestamps of comments for each student. Students sorted alphabetically and timestamps"\
                     + " sorted in reverse chronology.\n")
        names  = []
        for thread in master:
            names = names + thread.get_users()
        names = list(set(names))
        names = sort_alphabetical(names)

        for name in names:
            times = []
            types = []
            writer.write("NAME: " + name + "\n")
            for thread in master:
                if name in thread.get_users():
                    temp_time, temp_type = thread.get_time_for_name(name)
                    times = times + temp_time
                    types = types + temp_type
            ## Need to sort these before reporting
            temp = times.copy()
            for i in range(len(times)):
                if times[i].find(" (") >=0:
                    k = times[i].find(" (")
                    temp[i] = temp[i][:k]

            final_times, final_types = zip(*sorted(zip(temp, types), key = lambda x: time.strptime(x[0], "%I:%M %p %b %d")))
            #temp.sort(key = lambda x: time.strptime(x, "%I:%M %p %b %d"), reverse = True)
            for i in range(len(final_times)):
                if final_types[i] == 1:
                    writer.write(final_times[i] + " - COMMENT\n")
                else:
                    writer.write(final_times[i] + " - REPLY\n")
        print("Output written to file " + args.verbose + ".")
        writer.close()
    elif args.full:
        writer = open(args.full, "w")
        for thread in master:
            writer.write("****\n")
            writer.write("SELECTED TEXT: " + thread.get_selected() + "\n")
            users = thread.get_users()
            comments = thread.get_comments()
            times = thread.get_times()
            for i in range(len(users)):
                writer.write(users[i] + " (" + times[i] + "):\n")
                writer.write(comments[i] + "\n")
        print("Output written to file " + args.full + ".")
        writer.close()
    else:
        names  = []
        for thread in master:
            names = names + thread.get_users()
        names = list(set(names))
        names = sort_alphabetical(names)
        comments = [0] * len(names)
        replies = [0] * len(names)
        # Loop through threads
        for thread in master:
            users = thread.get_users()
            for i in range(len(users)):
                if i == 0:
                    loc = names.index(users[i])
                    comments[loc] = comments[loc] + 1
                else:
                    replies[loc] = replies[loc] + 1
        print("Statistics of all students, with number of comments and replies.")
        print ('%-40s%-30s%-30s' % ("Name", "Number of Comments", "Number of Replies"))

        for i in range(len(names)):
            print ('%-40s%-30i%-30i' % (str(names[i]), comments[i], replies[i]))

if __name__ == '__main__':
    main()
