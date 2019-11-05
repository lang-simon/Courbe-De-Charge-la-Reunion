# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 23:49:17 2019

@author: Simon
"""
from math import ceil
from datetime import timedelta
import datetime
import matplotlib as mp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

dateparse = lambda x: pd.datetime.strptime(x, '%Y-%m-%dT%H:%M:%S+04:00')
##########################RESTE A FAIRE###########################
#Gestion du Photovoltaique avec stockage
#################################################################


##################Structure du code#############################
#1- On regarde le fatal de 2018. On considere que de facon horaire ce sera la meme chose en 2028
#2-1-On regarde les différents moyens de prod
#2-2- On empile par prix croissant les productions dispatchable avec le diesel qui n'augmente que par tranche de 17MW
#3- On vérifie que toute tranche Diesel de 17MW est allumée au moins 3h, sinon on l'éteint et on remplace par TAC
#Pour faire tout ceci, on crée des nouvelles colonnes pour chaque centrale avec sa production horaire, une colonne avec le nombre de groupe diesel, et une colonne prix (prix marginal maximum)
#Hydraulique : on considère la meme production journalière et on la repartit mieux sur la journée
#    #1- On fait le dispatching normal sans hydro ( avec fermeture de centrales diesel si peu de temps)
#    #2- On remplace si il y a TAC par Hyddro
#    #3 si il reste de l'hydro dispo, on remplace du diesel
################################################################# 


#################FONCTION AUXILIAIRES####################
def update(data,colname, row,value):
    data.iloc[row, data.columns.get_loc(colname)]=value
def get(data,colname, row):
    return data.iloc[row, data.columns.get_loc(colname)]     #
#############################################################

#####################################LECTURE DU FICHIER ###########################################
orig=pd.read_csv('EDF_conso_2018.csv',';',parse_dates=['Date - Heure'], date_parser=dateparse)
orig=orig.iloc[:,[2,3,4,5,6,7,8,9,10]]
orig=orig.sort_values("Date - Heure",ascending=True)
####################################################################################################


###############VARIABLES########################
k=1.25 #Augmentation de la conso  2028/201     #
date_beg="2018-12-10"                          #
date_fin="2018-12-17"                          #
################################################

###################INITIALISATION#############################################################
date_beg=datetime.datetime.strptime(date_beg, '%Y-%m-%d')                                    #
date_fin=datetime.datetime.strptime(date_fin, '%Y-%m-%d')                                    #
orig=orig.loc[(orig['Date - Heure'] >=date_beg) & (orig['Date - Heure'] <=date_fin)]         #
data=orig.set_index("Date - Heure")                                                          #
data["cout marginal"]=0 #sans compter subventions enR                                                 #
data["nbrcentralediesel"]=0                                                                  #
data["Hydro"]=0
data["fatal"]=data.iloc[:,4]+data.iloc[:,5]+data.iloc[:,6]+data.iloc[:,7] #TOTAL FATAL sans hydro #
#data["Photovoltaïque (MW)"]+=data["Photovoltaïque avec stockage (MW)"]
##############################################################################################

###################PARC DE PRODUCTION#############################################################
moy_prod=pd.DataFrame(np.array([[2000,200,'red',0],[200, 211*0.9, 'red',0],[350,120*0.9,'crimson',0],[0,190, 'yellow',4], [0,10,'green',6],[130,(156+46)*0.9,'sienna',0],[0,1.5,'green',7]]),columns=["cout marginal","capa","couleur","2018"],index=["Defaillance","Diesel","TAC","PV","Eolien","Charbon","Biogaz"])   
moy_prod["cout marginal"]=moy_prod["cout marginal"].astype(float)
moy_prod["capa"]=moy_prod["capa"].astype(float)
moy_prod["2018"]=moy_prod["2018"].astype(int)
moy_prod=moy_prod.sort_values("cout marginal")
for a,b in moy_prod.iterrows():
    data[b.name]=0
    
    
####################################################################################################
     
#########################################EMPILEMENT CONSO###########################################
for i in range(len(data)):
    #On prend la conso (hors production fatale à la meme date de 2018)
    fat=get(data,"fatal",i)
    conso=data.iloc[i,0]*k-fat
    prod=0
    for a,row in moy_prod.iterrows():
        
        ####ENR####
        if row["cout marginal"]==0: #Si Prioritaire ( ie EnR)
            prodenr=max(data.iloc[i,row["2018"]],0)
            update(data,row.name,i,prodenr) # On met la prod EnR       
        #####DISPATCHABLE   
        elif prod<conso:
            update(data,"cout marginal",i,row["cout marginal"]) #le prix marginal sera au moins au prix de cette ressource
            
            if row["capa"]<conso-prod and row.name!="Diesel" : # on utilise cette centrale à fond si besoin
                prod=prod+row["capa"]
                update(data,row.name,i,row["capa"]) 
                
            else: # on n'utilise pas le moyen à fond donc on comble partiellement
                if row.name=="Diesel": # Si Diesel on compte le nombre de groupe diesel allumés
                    prodiesel=min(conso-prod,row["capa"])
                    nbr=ceil(prodiesel/17)
                    update(data,row.name,i,prodiesel) #on comble par tranche de centrale de 17
                    update(data,"nbrcentralediesel",i,nbr)
                    prod=prod+prodiesel
                    
                else :
                    update(data,row.name,i,conso-prod)
                    prod=conso
#####################################################################################################
                    
                    
###################################GESTION DES DIESELS ##############################################
for i in range(len(data)):#On va regarder si on allume une centrale uniquement pour qqs heures
   nbr= get(data,"nbrcentralediesel",i)
   a=False
   while nbr>get(data,"nbrcentralediesel",i-1) and not(a):#allumage de centrale
        if (nbr>get(data,"nbrcentralediesel",i+1)) or (nbr>get(data,"nbrcentralediesel",i+2) or nbr>get(data,"nbrcentralediesel",i+3)): #centrale allumée moins de 3h
            prod_diesel=get(data,"Diesel",i)-(nbr-1)*17  #prod diesel de la derniere centrale
            if (moy_prod.loc["TAC","capa"]-get(data,"TAC",i))>prod_diesel: #si on peut remplacer ce groupe par du TAC
                nbr=nbr-1
                update(data,"nbrcentralediesel",i,nbr)
                update(data,"Diesel",i,(nbr)*17)
                update(data,"TAC",i,get(data,"TAC",i)+prod_diesel)  
            else:
                a=True   
        else:
            a=True
######################################################################################################        
print ("Diesel optimisé")  


     
if True :        
    ######################################GESTION DE L HYDRO##############################################
    for i in range((date_fin-date_beg).days): # on va calculer la prod hydro de chaque journée et mieux la repartir
        if i%10==0 :
            print(i, "e jour d'hydro optimisé")
        date=(date_beg+timedelta(i)).strftime('%Y-%m-%d')
        prod_quot_hydro=data.loc[date:date]["Hydraulique (MW)"].sum()
        ############BLACK OUT#####################
        if(data.loc[date:date,"Defaillance"].sum()>0):
            for j in range(24):
                if(data.loc[date:date,"Defaillance"][j]>0):
                    Defaillance=data.loc[date:date,"Defaillance"][j]
                    hydro_prod=min(data.loc[date:date,"Defaillance"][j],prod_quot_hydro,120-data.loc[date:date,"Hydro"][j])# On peut etre limite entre : la puissance max des barrages, la capacité max quotidienne, ou la quantité de TAC à remplacer
                    data.loc[date:date,"Defaillance"][j]-=hydro_prod
                    prod_quot_hydro-=hydro_prod
                    data.loc[date:date,"Hydro"][j]+=hydro_prod
                    Defaillance-=hydro_prod
                    if Defaillance==0:
                        data.loc[date:date,"cout marginal"][j]=moy_prod.loc["TAC","cout marginal"] #Si plus de Defaillance on passe au prix de TAC

                       ############TURBINE A COMBUSTION############
        for j in range(24): # on remplace toute la TAC possible par de l'hydro
            tac=data.loc[date:date,"TAC"][j]
            if tac!=0 and prod_quot_hydro!=0 :
                hydro_prod=min(tac,prod_quot_hydro,120-data.loc[date:date,"Hydro"][j])# On peut etre limite entre : la puissance max des barrages, la capacité max quotidienne, ou la quantité de TAC à remplacer
                data.loc[date:date,"TAC"][j]-=hydro_prod
                prod_quot_hydro-=hydro_prod
                data.loc[date:date,"Hydro"][j]+=hydro_prod
                tac-=hydro_prod
                if tac==0:
                    data.loc[date:date,"cout marginal"][j]=moy_prod.loc["Diesel","cout marginal"] #si plus de TAC on passe au prix du diesel
        #################DIESEL########################        
        if prod_quot_hydro!=0: #Si aprés suppression de la TAC il en reste => On enleve du Diesel
             #Si on utilise du Diesel ce jour là
             while data.loc[date:date,"Diesel"].sum()>0 and prod_quot_hydro!=0 :
                for j in range(24):
                    diesel_heure=data.loc[date:date,"Diesel"][j] #Si on utilise du Diesel cette heure là
                    prod_diesel=diesel_heure-(data.loc[date:date,"nbrcentralediesel"][j]-1)*17 #prod de la derniere centrale diesel
                    if diesel_heure>0 and prod_quot_hydro!=0 :
                        hydro_prod=min(prod_quot_hydro,120-data.loc[date:date,"Hydro"][j],prod_diesel)
                        if hydro_prod!=0:
                            data.loc[date:date,"Diesel"][j]-=hydro_prod
                            prod_quot_hydro-=hydro_prod
                            data.loc[date:date,"nbrcentralediesel"][j]-=1
                            data.loc[date:date,"Hydro"][j]+=hydro_prod
    #######################################################################################################################
print ("Hydro optimisé")  

#####GRAPHS           
data["cout moyen de production"]=(227*data["Diesel"]+620*data["TAC"]+169*data["Charbon"]+189*data["Hydro"]+105*data["Biogaz"]+474*data["PV"]+250*data["Eolien"])/k/data["Production totale (MW)"]  #Avec le Defaillancen prix pour le PV
data["Conso"]=data["Diesel"]+data["TAC"]+data["Charbon"]+data["Hydro"]+data["Biogaz"]+data["PV"]+data["Eolien"] #Avec le Defaillancen prix pour le PV


data.iloc[:,[2,3,4,5,6,7]]=abs((data.iloc[:,[2,3,4,5,6,7]]))
fig, axs = plt.subplots(2,gridspec_kw={'height_ratios': [3, 1]})
ax,ax3=axs[0],axs[1]
gs1 = gridspec.GridSpec(1, 2)
gs1.update(hspace=0)

ax.set_ylabel("Consommation (MW)") 
#rspine = ax3.spines['right']
#ax3.set_frame_on(True)
#ax3.patch.set_visible(False)
ax3.set_ylabel("Prix euro/MWh")
fig.subplots_adjust(right=0.7)
data.iloc[:,[13,12,14,15,16,10,17,18]].plot.area(figsize=(16, 10),ax=ax,linewidth=0,color=["blue","yellow","green","saddlebrown","darkorange","royalblue","magenta","black"])  
#data["prix"].plot(ax=ax3,color='r', ylim=[0,450])
ax.set_xticklabels([])
ax.xaxis.set_visible(False)

data["Co2"]=(227*data["Diesel"]+620*data["TAC"]+169*data["Charbon"]+189*data["Hydro"]+105*data["Biogaz"]+474*data["PV"]+250*data["Eolien"])
data["Conso"].plot(ax=ax,color="r")
data["cout moyen de production"].plot(ax=ax3,color='b',legend=True, ylim=[100,400])
data["cout marginal"].plot(ax=ax3,color='black',legend=True, ylim=[100,400])
ax3.legend(loc=1)
ax.legend(loc="lower left")
ax.set_title("Semaine d'Hiver en 2028")

plt.subplots_adjust(wspace=0, hspace=0)

plt.show()
print( "Les TAC ont fonctionné",data[data["TAC"]>0].count().mean(),"heures pour un total prévu de 800 annuelles")
    
#    
#    
#    
#centrale=["Diesel","TAC","Bagasse/CharDefaillancen","Hydro Dispatch","Hydro Fatal","PV","PV avec stockage","Éolien","Bioénergies","Batteries"]
#


#
#data["Photovoltaïque avec stockage (MW)"]=abs(data["Photovoltaïque avec stockage (MW)"])
#data["Eolien (MW)"]=abs(data["Eolien (MW)"])
#data["Photovoltaïque (MW)"]=abs(data["Photovoltaïque (MW)"])
#data=data.sort_values("Date - Heure",ascending=True)
#data=data.reset_index(drop=True)
#bb=data.set_index("Date - Heure")
#
#bb.iloc[:, ::-1].drop("Production totale (MW)", axis=1).plot.area(color=['g','green','yellow','yellow','dodgerblue','sienna','red'])



####TRACER LE MONOTONE 
#data=pd.read_csv('EDF_conso_2018.csv',';')
#data=data.iloc[:,[3,6,7,8,9,10]]
#data=data.sort_values("Production totale (MW)",ascending=False)
#data=data.reset_index(drop=True)
#data["Production totale 2028 tendanciel (MW)"]=data["Production totale (MW)"]*1.24
#plt.figure()
#ax=data["Production totale (MW)"].plot(title="Monotone de la Consommation en 2018",legend=True,ylim=[0,700],xlim=[0,9000])
#ax.set_xlabel("Heures")
#ax.set_ylabel("Consommation (MW)")
#data["fatal"]=0.5*data.iloc[:,1]+data.iloc[:,2]+data.iloc[:,3]+data.iloc[:,4]+data.iloc[:,5]
#data["Prod_2018_hors_fatal"]=data["Production totale (MW)"]-data["fatal"]
#data["Prod_2028_hors_fatal"]=data["Production totale 2028 tendanciel (MW)"]-data["fatal"]#si pas investissement dans FATAL
#data=data.sort_values("Prod_2018_hors_fatal",ascending=False)
#data=data.reset_index(drop=True)
#ax=data["Prod_2018_hors_fatal"].plot(legend=True)
#plt.figure()
#data=data.sort_values("Production totale (MW)",ascending=False)
#data=data.reset_index(drop=True)
#bx=data["Production totale 2028 tendanciel (MW)"].plot(title="Monotone de la Consommation en 2028 tendanciel",legend=True,ylim=[0,700],xlim=[0,9000])
#bx.set_xlabel("Heures")
#bx.set_ylabel("Consommation (MW)")
#data=data.sort_values("Prod_2028_hors_fatal",ascending=False)
#data=data.reset_index(drop=True)
#bx=data["Prod_2028_hors_fatal"].plot(legend=True)




