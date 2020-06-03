



data = open('data')
i = 1
for st in data:
    out=open(str(i)+".txt","w")
    print(st, file=out)
    i += 1
