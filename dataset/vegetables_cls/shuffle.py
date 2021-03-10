import random

out = open("./train_list_shuffle.txt",'w')
lines=[]
with open("./train_list.txt", 'r') as infile:
   for line in infile:
      lines.append(line)
random.shuffle(lines)

for line in lines:
   out.write(line) 

