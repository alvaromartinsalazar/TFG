import urllib, urllib.request
from bs4 import BeautifulSoup

url = 'https://www.pisos.com/viviendas/sevilla/'
html = urllib.request.urlopen(url)
soup = BeautifulSoup(html)

tags=soup('div')
zonas = soup.find(class_='zoneList')

for tag in tags:
    tags2=zonas('a')
    for tag2 in tags2:
        enlaces_zonas=tag2.get('href')
        tags3='https://www.pisos.com'+enlaces_zonas
        print(tags3)
        
        

    
