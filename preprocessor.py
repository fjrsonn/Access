# preprocessor.py (corrigido)
# Funções para extrair nome, placa, bloco, apartamento, modelos, cor e status
# Exporta: extrair_tudo_consumo, VEICULOS_MAP, remover_status, detectar_status

import re
from typing import Dict, Any, List, Tuple

# mapa simples de modelos -> abreviações/comuns (aumente conforme necessário)
VEICULOS_MAP = {
    "ONIX": ["ONIX","ONI","ONX","ONICS","ONIX LT","ONIX PLUS"],
    "CORSA": ["CORSA","COR","CRSA","CORZA"],
    "CRUZE": ["CRUZE","CRUZ","CRUS","CRZE"],
    "CELTA": ["CELTA","CELT","CLTA"],
    "PRISMA": ["PRISMA","PRISM","PRZMA"],
    "SPIN": ["SPIN","SPN"],
    "S10": ["S10","S-10","S 10"],
    "CLASSIC": ["CLASSIC","CLASIC","CLSIC"],
    "NIVUS": ["NIVUS","NIV","NVS"],
    "VIRTUS": ["VIRTUS","VIRT","VIRTS","VIR"],
    "POLO": ["POLO","POL","PLO","POLL"],
    "GOL": ["GOL","GOOL","GL"],
    "JETTA": ["JETTA","JET","JETA","JTA"],
    "SAVEIRO": ["SAVEIRO","SAVEIR","SAVERO"],
    "VOYAGE": ["VOYAGE","VOIAGE","VYAGE"],
    "FOX": ["FOX","FOXX"],
    "UP": ["UP","UP!"],
    "MOBI": ["MOBI","MOB","MBI","MOBBY"],
    "UNO": ["UNO","UN","UUNO"],
    "ARGO": ["ARGO","ARG","AROG"],
    "PALIO": ["PALIO","PAL","PLIO"],
    "SIENA": ["SIENA","SENA","SINA"],
    "STRADA": ["STRADA","STRD","STRDA"],
    "TORO": ["TORO","TOR","TRO"],
    "CRONOS": ["CRONOS","CRONO","CRNS"],
    "IDEA": ["IDEA","IDA"],
    "HB20": ["HB20","HB 20","H B 20","HB2O","HB-20"],
    "CRETA": ["CRETA","CRET","CRTA"],
    "IX35": ["IX35","IX 35","I X 35"],
    "KA": ["KA","KÁ","K","FORD KA"],
    "FIESTA": ["FIESTA","FIEST","FSTA"],
    "ECOSPORT": ["ECOSPORT","ECO","ECOSP","ECOS"],
    "RANGER": ["RANGER","RANGR"],
    "COROLLA": ["COROLLA","COROLA","CORLLA"],
    "ETIOS": ["ETIOS","ETIO","ETIUS"],
    "HILUX": ["HILUX","HILUXX","HLUX"],
    "YARIS": ["YARIS","YRS","IARIS"],
    "CIVIC": ["CIVIC","CIV","CIVIK","CIVC"],
    "FIT": ["FIT","FITT"],
    "HRV": ["HRV","H-RV","H R V"],
    "CITY": ["CITY","CTY"],
    "SANDERO": ["SANDERO","SAND","SNDR"],
    "LOGAN": ["LOGAN","LOG","LAGN"],
    "KWID": ["KWID","KWD","QUID"],
    "DUSTER": ["DUSTER","DUST","DSTR"],
    "MOTO": ["MOTO","MOT","MOTOR","MOTOCICLETA"],
    "T-CROSS": ["T-CROSS", "TCROSS", "T CROSS", "T-CROS", "TCRUZ"],
    "COMPASS": ["COMPASS", "COMPAS", "COMPASO"],
    "RENEGADE": ["RENEGADE", "RENEGAD"],
    "TRACKER": ["TRACKER", "TRAKER", "TRAQUER"],
    "KICKS": ["KICKS", "KIKIS", "KIX"],
    "FASTBACK": ["FASTBACK", "FASTBAK", "FESTBACK"],
    "PULSE": ["PULSE", "PULSI", "PULZ"],
    "COROLLA CROSS": ["COROLLA CROSS", "COROLLACROSS", "COROLLA"],
    "TIGGO 5X": ["TIGGO 5X", "TIGGO5X", "TIGGO"],
    "DOLPHIN": ["DOLPHIN"],
    "SONG PLUS": ["SONG PLUS", "SONGPLUS", "SONG"],
    "HAVAL H6": ["HAVAL H6", "HAVALH6", "HAVAL"],
    "CG 160": ["CG 160", "CG160", "CG"],
    "BIZ": ["BIZ", "BIS"],
    "POP 110I": ["POP 110I", "POP110I", "POP"],
    "NXR 160 BROS": ["NXR 160 BROS", "NXR160BROS", "NXR"],
    "CB 300F TWISTER": ["CB 300F TWISTER", "CB300FTWISTER", "CB"],
    "PCX 160": ["PCX 160", "PCX160", "PCX"],
    "FAZER FZ25": ["FAZER FZ25", "FAZERFZ25", "FAZER"],
    "CROSSER 150": ["CROSSER 150", "CROSSER150", "CROSSER"],
    "FACTOR 150": ["FACTOR 150", "FACTOR150", "FACTOR"],
    "LANDER 250": ["LANDER 250", "LANDER250", "LANDER"],
    "SPORT 110I": ["SPORT 110I", "SPORT110I", "SPORT"],
    "XY 125": ["XY 125", "XY125", "XY"],
    "FIORINO": ["FIORINO", "FIORIN"],
    "MASTER": ["MASTER", "MASTR"],
    "DUCATO": ["DUCATO", "DUCATTO"],
    "SPRINTER": ["SPRINTER", "SPRINT", "ESPRINTER"],
    "DAILY": ["DAILY", "DAILI", "DAYLI"],
    "HR": ["HR"],
    "BONGO": ["BONGO", "BONGU"],
    "EXPERT": ["EXPERT", "EXPER"],
    "JUMPY": ["JUMPY", "JUMPI"],
    "TRANSIT": ["TRANSIT", "TRANZIT"],
    "DELIVERY": ["DELIVERY", "DELIVERI", "DELIVER"],
    "ACCELO": ["ACCELO", "ACELO", "ACCELLO"],
    "F-350": ["F-350", "F350"],
    "F-4000": ["F-4000", "F4000"],
    "TUCSON": ["TUCSON"],
    "SANTA FE": ["SANTA FE", "SANTAFE", "SANTA", "SANTA FÉ"],
    "AZERA": ["AZERA", "AZERRA"],
    "ELANTRA": ["ELANTRA"],
    "I30": ["I30"],
    "KONA": ["KONA"],
    "IONIQ": ["IONIQ"],
    "CR-V": ["CR-V", "CRV", "C R V"],
    "WR-V": ["WR-V", "WRV", "W R V"],
    "ACCORD": ["ACCORD", "ACORD"],
    "ZR-V": ["ZR-V", "ZRV", "Z R V"],
    "TAOS": ["TAOS", "TAO"],
    "TIGUAN": ["TIGUAN", "TIGUÃ"],
    "AMAROK": ["AMAROK", "AMAROC"],
    "PASSAT": ["PASSAT", "PASAT"],
    "GOLF": ["GOLF"],
    "SANTANA": ["SANTANA"],
    "FUSCA": ["FUSCA", "FUSKA"],
    "KOMBI": ["KOMBI", "COMBY", "COMBI"],
    "MAREA": ["MAREA"],
    "TEMPRA": ["TEMPRA"],
    "STILO": ["STILO"],
    "BRAVO": ["BRAVO"],
    "LINEA": ["LINEA"],
    "500": ["500", "CINQUECENTO", "FIAT 500"],
    "TITANO": ["TITANO"],
    "SCUDO": ["SCUDO"],
    "MONTANA": ["MONTANA", "MONTANNA"],
    "EQUINOX": ["EQUINOX"],
    "TRAILBLAZER": ["TRAILBLAZER", "TRAILBLASER", "TRAIL"],
    "SILVERADO": ["SILVERADO", "SILVERADDO"],
    "ASTRA": ["ASTRA"],
    "VECTRA": ["VECTRA", "VEKTRA"],
    "MERIVA": ["MERIVA"],
    "ZAFIRA": ["ZAFIRA"],
    "CAPTIVA": ["CAPTIVA"],
    "CAMARO": ["CAMARO", "CAMARRO"],
    "TERRITORY": ["TERRITORY", "TERRITORI"],
    "MAVERICK": ["MAVERICK", "MAVERIK"],
    "BRONCO SPORT": ["BRONCO SPORT", "BRONCOSPORT", "BRONCO"],
    "MUSTANG": ["MUSTANG", "MUSTANGUE"],
    "FOCUS": ["FOCUS", "FOKUS"],
    "FUSION": ["FUSION", "FUZION"],
    "EDGE": ["EDGE"],
    "F-150": ["F-150", "F150"],
    "F-250": ["F-250", "F250"],
    "OROCH": ["OROCH", "OROCK"],
    "KARDIAN": ["KARDIAN"],
    "KANGOO": ["KANGOO", "KANGU"],
    "MEGANE": ["MEGANE"],
    "SCENIC": ["SCENIC"],
    "FLUENCE": ["FLUENCE", "FLUENCI"],
    "CAPTUR": ["CAPTUR", "CAPTURE"],
    "208": ["208"],
    "2008": ["2008"],
    "3008": ["3008"],
    "5008": ["5008"],
    "PARTNER": ["PARTNER", "PARTINER"],
    "BOXER": ["BOXER", "BOKSER"],
    "206": ["206"],
    "207": ["207"],
    "307": ["307"],
    "308": ["308"],
    "408": ["408"],
    "320I": ["320I", "320"],
    "X1": ["X1"],
    "X3": ["X3"],
    "X5": ["X5"],
    "X6": ["X6"],
    "M3": ["M3"],
    "M5": ["M5"],
    "Z4": ["Z4"],
    "I3": ["I3"],
    "IX": ["IX"],
    "A3": ["A3"],
    "A4": ["A4"],
    "A5": ["A5"],
    "Q3": ["Q3"],
    "Q5": ["Q5"],
    "Q7": ["Q7"],
    "Q8": ["Q8"],
    "E-TRON": ["E-TRON", "ETRON"],
    "TT": ["TT"],
    "R8": ["R8"],
    "SEAL": ["SEAL", "SIAL"],
    "YUAN PLUS": ["YUAN PLUS", "YUANPLUS", "YUAN"],
    "TAN": ["TAN"],
    "HAN": ["HAN"],
    "KING": ["KING"],
    "SHARK": ["SHARK"],
    "MONSTER": ["MONSTER", "MONSTR"],
    "PANIGALE": ["PANIGALE", "PANIGAL"],
    "MULTISTRADA": ["MULTISTRADA"],
    "SCRAMBLER": ["SCRAMBLER"],
    "DIAVEL": ["DIAVEL"],
    "TIGER 900": ["TIGER 900", "TIGER900", "TIGER"],
    "TIGER 1200": ["TIGER 1200", "TIGER1200", "TIGER"],
    "STREET TRIPLE": ["STREET TRIPLE", "STREETTRIPLE", "STREET"],
    "SPEED TRIPLE": ["SPEED TRIPLE", "SPEEDTRIPLE", "SPEED"],
    "BONNEVILLE": ["BONNEVILLE", "BONEVILLE"],
    "TRIDENT 660": ["TRIDENT 660", "TRIDENT660", "TRIDENT"],
    "SCRAMBLER 400X": ["SCRAMBLER 400X", "SCRAMBLER400X", "SCRAMBLER"],
    "SPEED 400": ["SPEED 400", "SPEED400", "SPEED"],
    "R 1250 GS": ["R 1250 GS", "R1250GS", "R", "GS 1250"],
    "R 1300 GS": ["R 1300 GS", "R1300GS", "R", "GS 1300"],
    "F 800 GS": ["F 800 GS", "F800GS", "F"],
    "F 900 GS": ["F 900 GS", "F900GS", "F"],
    "G 310 GS": ["G 310 GS", "G310GS", "G"],
    "S 1000 RR": ["S 1000 RR", "S1000RR", "S", "S1000"],
    "XRE 300": ["XRE 300", "XRE300", "XRE"],
    "XRE 190": ["XRE 190", "XRE190", "XRE"],
    "SAHARA 300": ["SAHARA 300", "SAHARA300", "SAHARA"],
    "CB 500": ["CB 500", "CB500", "CB"],
    "CB 650R": ["CB 650R", "CB650R", "CB"],
    "NC 750X": ["NC 750X", "NC750X", "NC"],
    "AFRICA TWIN": ["AFRICA TWIN", "AFRICATWIN", "AFRICA"],
    "HORNET": ["HORNET", "ORNET"],
    "MT-03": ["MT-03", "MT03", "MT 03"],
    "MT-07": ["MT-07", "MT07", "MT 07"],
    "MT-09": ["MT-09", "MT09", "MT 09"],
    "R3": ["R3"],
    "NMAX": ["NMAX", "N-MAX", "N MAX"],
    "XMAX": ["XMAX", "X-MAX", "X MAX"],
    "TENERE 700": ["TENERE 700", "TENERE700", "TENERE"],
    "NINJA 400": ["NINJA 400", "NINJA400", "NINJA"],
    "NINJA 650": ["NINJA 650", "NINJA650", "NINJA"],
    "Z400": ["Z400"],
    "Z900": ["Z900"],
    "VERSYS 650": ["VERSYS 650", "VERSYS650", "VERSYS"],
    "V-STROM": ["V-STROM", "VSTROM"],
    "HAYABUSA": ["HAYABUSA", "HAIABUSA"],
    "GSX-S": ["GSX-S", "GSXS"],
    "FAT BOY": ["FAT BOY", "FATBOY", "FAT"],
    "IRON 883": ["IRON 883", "IRON883", "IRON"],
    "HERITAGE SOFTAL": ["HERITAGE SOFTAL", "HERITAGESOFTAL", "HERITAGE"],
    "ROAD KING": ["ROAD KING", "ROADKING", "ROAD"]
}

# cores comuns (pt-BR)
_CORES = {
    "BRANCO": ["BRANCO", "BRANCA", "BRANC", "BRANCO PEROLIZADO", "BRANCO METALICO", "BRANCO SOLIDO", "BRANCO TAFETA", "BRANCO ESTELAR"],
    "PRETO": ["PRETO", "PRETA", "PRET", "PRETO METALICO", "PRETO PEROLIZADO", "PRETO FOSCO", "PRETO NINJA", "PRETO ECLIPSE"],
    "PRATA": ["PRATA", "PRAT", "PRATEADO", "PRATEADA", "PRATA METALICO", "PRATA BARI", "PRATA SIRIUS"],
    "CINZA": ["CINZA", "CINZ", "CINZA METALICO", "CINZA GRAFITE", "CINZA BARIUM", "CINZA MOONLIGHT", "CINZA PLATINUM"],
    "VERMELHO": ["VERMELHO", "VERMELHA", "VERM", "VERMELHO METALICO", "VERMELHO PEROLIZADO", "VERMELHO FOGO", "VERMELHO TRIBAL"],
    "AZUL": ["AZUL", "AZU", "AZUL METALICO", "AZUL PEROLIZADO", "AZUL MARINHO", "AZUL CELESTE", "AZUL COSMOS"],
    "VERDE": ["VERDE", "VERD", "VERDE METALICO", "VERDE MUSGO", "VERDE FLORESTA", "VERDE MANTIQUEIRA"],
    "AMARELO": ["AMARELO", "AMARELA", "AMAR", "AMARELO METALICO", "AMARELO CANARIO", "AMARELO SOLAR"],
    "LARANJA": ["LARANJA", "LARANJ", "LARANJA METALICO", "LARANJA VIBRANTE", "LARANJA TERRA"],
    "MARROM": ["MARROM", "MARRON", "MARROM METALICO", "MARROM TERRA", "MARROM CAFE"],
    "BEGE": ["BEGE", "BEG", "BEGE METALICO", "BEGE AREIA", "BEGE CHAMPAGNE"],
    "DOURADO": ["DOURADO", "DOURADA", "DOUR", "DOURADO METALICO"],
    "VINHO": ["VINHO", "VINH", "BORDEAUX", "BORDO"],
    "ROSA": ["ROSA", "PINK"],
    "ROXO": ["ROXO", "ROXA", "VIOLETA"],
    "FANTASIA": ["FANTASIA", "COLORIDO", "MULTICOR"]
}
_CORES_SET = set([c.upper() for c in _CORES])

# palavras de status
_STATUS_MAP = {
    "VISITANTE": ["VISITANTE", "VISIT", "VIS", "VST", "VISI", "VI", "VISITANT", "VISITAN", "VISITA", "VISITNTE", "VISITTE", "VISITNE", "VISITANET", "VISITN", "VSTANTE", "VISITANTY"],
    "MORADOR": ["MORADOR", "MOR", "MORA", "M", "MORADO", "MORAD", "MRADOR", "MOADOR", "MORADR", "MORADRO", "MORADORES", "MORADORA"],
    "PRESTADOR DE SERVIÇO": ["PRESTADOR DE SERVIÇO", "PRESTADOR DE SERVICO", "PREST", "PRES", "SERV", "FUNC", "FORN", "TERC", "PRESTADOR", "SERVICO", "SERVIÇO", "PREST SERVICO", "PREST SERVIÇO", "P.S", "PS", "PRESTADR", "PRESTADO", "SERVIC", "SERVIÇ", "PRESTADRO", "PRESTADORES", "PRESTADORA", "FORNECEDOR", "FUNCIONARIO", "TERCEIRIZADO", "TERCEIRO"],
    "DESCONHECIDO": ["DESCONHECIDO","?"]
}

_STATUS_WORDS = set()
for k,v in _STATUS_MAP.items():
    for w in v:
        _STATUS_WORDS.add(w.upper())

_NOMES = {
    "JOSÉ": ["JOSE", "JOZE", "JOZEH", "JOSEH", "JSE", "JOE", "JOS"],
    "JOÃO": ["JOAO", "JOAUM", "JOAM", "JAO", "JAA", "JOA"],
    "MARIA": ["MARIA", "MARYA", "MARI", "MRIA", "MAIA", "MRA", "MAR"],
    "ANTÔNIO": ["ANTONIO", "ANTUNIO", "ANTÔNIO", "ATONIO", "ANONIO", "ANTNIO", "ANTOIO", "ANTONO", "ANTONI"],
    "FRANCISCO": ["FRANCISCO", "FRANCICO", "FRANSCISCO", "FANCISCO", "FRNCISCO", "FRAISCO", "FRANCSCO", "FRANCISC"],
    "PEDRO": ["PEDRO", "PEDRU", "PDRO", "PERO", "PEDO", "PEDR"],
    "LUIZ": ["LUIZ", "LUIS", "LIZ", "LUZ", "LUI"],
    "LUCAS": ["LUCAS", "LUKAS", "LCAS", "LUAS", "LUCS", "LUC"],
    "CARLOS": ["CARLOS", "KARLOS", "CALOS", "CAOS", "CARS", "CARL"],
    "ANA": ["ANA", "ANNA", "NA", "AA", "AN"],
    "PAULO": ["PAULO", "PAULU", "PULO", "PALO", "PAUO", "PAUL"],
    "MARCOS": ["MARCOS", "MARKOS", "MRCOS", "MACOS", "MARCS", "MARCO"],
    "RAFAEL": ["RAFAEL", "RAPHAEL", "RFAEL", "RAAEL", "RAFEL", "RAFAEL"],
    "GABRIEL": ["GABRIEL", "GABRYEL", "GABRIEL", "GBRIEL", "GAREL", "GABREL", "GABRIL", "GABRIE"],
    "HELENA": ["HELENA", "ELENA", "HLENA", "HEENA", "HELNA", "HELEA", "HELEN"],
    "ALICE": ["ALICE", "ALYCE", "LICE", "AICE", "ALCE", "ALIE", "ALIC"],
    "LAURA": ["LAURA", "LURA", "LARA", "LAUA", "LAUR"],
    "VALENTINA": ["VALENTINA", "VALENTYNA", "ALENTINA", "VLENTINA", "VAENTINA", "VALNTINA", "VALETINA", "VALENINA", "VALENTNA", "VALENTIA", "VALENTIN"],
    "ENZO": ["ENZO", "ENSO", "NZO", "EZO", "ENZ"],
    "ARTHUR": ["ARTHUR", "ARTUR", "ARTHUR", "RTHUR", "ATHUR", "ARHR", "ARTUR"],
    "FELIPE": ["FELIPE", "PHELIPE", "FELLIPE", "PHELLIPE", "FLIPE", "FEIPE", "FELPE", "FELIE", "FELIP"],
    "GUILHERME": ["GUILHERME", "GUILERME", "UILHERME", "GILHERME", "GUHERME", "GUILRME", "GUILEME", "GUILHRE", "GUILHEM", "GUILHERM"],
    "THIAGO": ["THIAGO", "TIAGO", "HIAGO", "TAGO", "THAO", "THIG", "THIAO"],
    "MATHEUS": ["MATHEUS", "MATEUS", "MTHEUS", "MAHEUS", "MATEUS", "MATHUS", "MATHEU"],
    "VITÓRIA": ["VITORIA", "VICTORIA", "VITORIA", "ITORIA", "VTORIA", "VIORIA", "VITRIA", "VITOIA", "VITORI"],
    "JÚLIA": ["JULIA", "GIULIA", "JULYA", "JULA", "JUI", "JULI"],
    "BEATRIZ": ["BEATRIZ", "BEATRIS", "EATRIZ", "BATRIZ", "BETRIZ", "BEAIRZ", "BEATRZ", "BEATRI"],
    "LETICIA": ["LETICIA", "LETYCIA", "ETICIA", "LTICIA", "LEICIA", "LETICA", "LETIIA", "LETICI"],
    "GUSTAVO": ["GUSTAVO", "USTAVO", "GSTAVO", "GUAVO", "GUSAVO", "GUSTVO", "GUSTAO", "GUSTAV"],
    "MURILO": ["MURILO", "URILO", "MRILO", "MUILO", "MURLO", "MURIO", "MURIL"],
    "CAIO": ["CAIO", "CIO", "CAO", "CAI"],
    "BRUNO": ["BRUNO", "RUNO", "BUNO", "BRNO", "BRUO", "BRUN"],
    "EDUARDO": ["EDUARDO", "DUARDO", "EUARDO", "EDARDO", "EDURDO", "EDUAO", "EDUARD"],
    "RODRIGO": ["RODRIGO", "ODRIGO", "RDRIGO", "ROIGO", "RODRGO", "RODRI", "RODRIG"],
    "DANIEL": ["DANIEL", "DNIEL", "DAIEL", "DANEL", "DANIL", "DANIE"],
    "MARCELO": ["MARCELO", "ARCELO", "MRCELO", "MARELO", "MARCLO", "MARCEO", "MARCEL"],
    "RICARDO": ["RICARDO", "ICARDO", "RCARDO", "RIARDO", "RICRDO", "RICAO", "RICARD"],
    "FERNANDO": ["FERNANDO", "ERNANDO", "FRNANDO", "FENANDO", "FERANDO", "FERNNDO", "FERNADO", "FERNAN"],
    "ALEXANDRE": ["ALEXANDRE", "LEXANDRE", "AEXANDRE", "ALXANDRE", "ALEANDRE", "ALEXNDRE", "ALEXADE", "ALEXANRE", "ALEXANDR"],
    "ROBERTO": ["ROBERTO", "OBERTO", "RBERTO", "ROERTO", "ROBRTO", "ROBEO", "ROBERT"],
    "CAMILA": ["CAMILA", "AMILA", "CMILA", "CAILA", "CAMLA", "CAMIA", "CAMIL"],
    "AMANDA": ["AMANDA", "MANDA", "AANDA", "AMNDA", "AMADA", "AMAN"],
    "JULIANA": ["JULIANA", "ULIANA", "JLIANA", "JUIANA", "JULANA", "JULINA", "JULIAA", "JULIAN"],
    "LARISSA": ["LARISSA", "ARISSA", "LRISSA", "LAISSA", "LARSSA", "LARISA", "LARISS"],
    "FERNANDA": ["FERNANDA", "ERNANDA", "FRNANDA", "FENANDA", "FERANDA", "FERNNDA", "FERNADA", "FERNANA", "FERNAND"],
    "PATRÍCIA": ["PATRICIA", "ATRICIA", "PTRICIA", "PARICIA", "PATICIA", "PATRCIA", "PATRIIA", "PATRICA", "PATRICI"],
    "ALINE": ["ALINE", "LINE", "AINE", "ALNE", "ALIE", "ALIN"],
    "BRUNA": ["BRUNA", "RUNA", "BUNA", "BRNA", "BRUA", "BRUN"],
    "VANESSA": ["VANESSA", "ANESSA", "VNESSA", "VAESSA", "VANSSA", "VANESA", "VANESS"],
    "DANIELA": ["DANIELA", "ANIELA", "DNIELA", "DAIELA", "DANELA", "DANILA", "DANIEA", "DANIEL"],
    "ISABELA": ["ISABELA", "SABELA", "IABELA", "ISBELA", "ISAELA", "ISABLA", "ISABEA", "ISABEL"],
    "GIOVANNA": ["GIOVANNA", "IOVANNA", "GOVANNA", "GIVANNA", "GIOANNA", "GIOVNNA", "GIOVANA", "GIOVANN"],
    "SABRÍNA": ["SABRINA", "ABRINA", "SBRINA", "SARINA", "SABINA", "SABRNA", "SABRIA", "SABRIN"],
    "TATIANE": ["TATIANE", "ATIANE", "TTIANE", "TAIANE", "TATANE", "TATINE", "TATIAE", "TATIAN"],
    "RENATA": ["RENATA", "ENATA", "RNATA", "REATA", "RENTA", "RENAA", "RENAT"],
    "SILVA": ["SILVA", "SYLVA", "ILVA", "SLVA", "SIVA", "SILA", "SILV"],
    "SANTOS": ["SANTOS", "ANTOS", "SNTOS", "SATOS", "SANOS", "SANTS", "SANTO"],
    "OLIVEIRA": ["OLIVEIRA", "LIVEIRA", "OIVEIRA", "OLVEIRA", "OLIEIRA", "OLIVIRA", "OLIVERA", "OLIVEIA", "OLIVEIR"],
    "SOUZA": ["SOUZA", "SOUSA", "OUZA", "SUZA", "SOZA", "SOUA", "SOUZ"],
    "PEREIRA": ["PEREIRA", "EREIRA", "PREIRA", "PEEIRA", "PERIRA", "PERERA", "PEREIA", "PEREIR"],
    "RODRIGUES": ["RODRIGUES", "RODRIGUEZ", "ODRIGUES", "RDRIGUES", "RORIGUES", "RODIGUES", "RODRGUES", "RODRIUES", "RODRIGES", "RODRIGUS", "RODRIGUE"],
    "ALVES": ["ALVES", "ALVIS", "LVES", "AVES", "ALES", "ALVS", "ALVE"],
    "NASCIMENTO": ["NASCIMENTO", "ASCIMENTO", "NSCIMENTO", "NACIMENTO", "NASIMENTO", "NASCMENTO", "NASCIENTO", "NASCIMNTO", "NASCIMETO", "NASCIMENO", "NASCIMENT"],
    "LIMA": ["LIMA", "LYMA", "IMA", "LMA", "LIA", "LIM"],
    "ARAÚJO": ["ARAUJO", "RAUJO", "AAUJO", "ARUJO", "ARAJO", "ARAUO", "ARAUJ"],
    "FERREIRA": ["FERREIRA", "ERREIRA", "FRREIRA", "FEREIRA", "FERRIRA", "FERRERA", "FERREIA", "FERREIR"],
    "RIBEIRO": ["RIBEIRO", "IBEIRO", "RBEIRO", "RIEIRO", "RIBIRO", "RIBERO", "RIBEIO", "RIBEIR"],
    "GOMES": ["GOMES", "OMES", "GMES", "GOES", "GOMS", "GOME"],
    "MARTINS": ["MARTINS", "ARTINS", "MRTINS", "MATINS", "MARINS", "MARTNS", "MARTIS", "MARTIN"],
    "ROCHA": ["ROCHA", "OCHA", "RCHA", "ROHA", "ROCA", "ROCH"],
    "CARVALHO": ["CARVALHO", "ARVALHO", "CRVALHO", "CAVALHO", "CARALHO", "CARVLHO", "CARVAHO", "CARVALO", "CARVALH"],
    "BARBOSA": ["BARBOSA", "BARBOZA", "ARBOSA", "BRBOSA", "BABOSA", "BAROSA", "BARBSA", "BARBOA", "BARBOS"],
    "CAVALCANTE": ["CAVALCANTE", "AVALCANTE", "CVALCANTE", "CAALCANTE", "CAVLCANTE", "CAVACANTE", "CAVALANTE", "CAVALCNTE", "CAVALCATE", "CAVALCANE", "CAVALCANT"],
    "DIAS": ["DIAS", "IAS", "DAS", "DIS", "DIA"],
    "MOREIRA": ["MOREIRA", "OREIRA", "MREIRA", "MOEIRA", "MORIRA", "MORERA", "MOREIA", "MOREIR"],
    "TEIXEIRA": ["TEIXEIRA", "EIXEIRA", "TIXEIRA", "TEXEIRA", "TEIEIRA", "TEIXIRA", "TEIXERA", "TEIXEIA", "TEIXEIR"],
    "VIEIRA": ["VIEIRA", "IEIRA", "VEIRA", "VIIRA", "VIERA", "VIEIA", "VIEIR"],
    "CORREIA": ["CORREIA", "ORREIA", "CRREIA", "COREIA", "CORRIA", "CORREA", "CORREI"],
    "MENDES": ["MENDES", "ENDES", "MNDES", "MEDES", "MENES", "MENDS", "MENDE"],
    "FREITAS": ["FREITAS", "REITAS", "FEITAS", "FRITAS", "FRETAS", "FREIAS", "FREITS", "FREITA"],
    "CARDOSO": ["CARDOSO", "ARDOSO", "CRDOSO", "CADOSO", "CAROSO", "CARDSO", "CARDOO", "CARDOS"],
    "COSTA": ["COSTA", "OSTA", "CSTA", "COTA", "COSA", "COST"],
    "MACHADO": ["MACHADO", "ACHADO", "MCHADO", "MAHADO", "MACADO", "MACHDO", "MACHAO", "MACHAD"],
    "FERNANDES": ["FERNANDES", "ERNANDES", "FRNANDES", "FENANDES", "FERANDES", "FERNNDES", "FERNADES", "FERNANES", "FERNANDS", "FERNANDE"],
    "LOPES": ["LOPES", "OPES", "LPES", "LOES", "LOPS", "LOPE"],
    "BATISTA": ["BATISTA", "ATISTA", "BTISTA", "BAISTA", "BATSTA", "BATITA", "BATISA", "BATIST"],
    "MARQUES": ["MARQUES", "ARQUES", "MRQUES", "MAQUES", "MARUES", "MARQES", "MARQUS", "MARQUE"],
    "SANTANA": ["SANTANA", "ANTANA", "SNTANA", "SATANA", "SANANA", "SANTNA", "SANTAA", "SANTAN"],
    "RAMOS": ["RAMOS", "AMOS", "RMOS", "RAOS", "RAMS", "RAMO"],
    "SOARES": ["SOARES", "OARES", "SARES", "SORES", "SOAES", "SOARS", "SOARE"],
    "MONTEIRO": ["MONTEIRO", "ONTEIRO", "MNTEIRO", "MOTEIRO", "MONEIRO", "MONTIRO", "MONTERO", "MONTEIO", "MONTEIR"],
    "FARIAS": ["FARIAS", "ARIAS", "FRIAS", "FAIAS", "FARAS", "FARIS", "FARIA"],
    "NEVES": ["NEVES", "EVES", "NVES", "NEES", "NEVS", "NEVE"],
    "GUIMARÃES": ["GUIMARAES", "UIMARAES", "GIMARAES", "GUMARAES", "GUIARAES", "GUIMRAES", "GUIMAAES", "GUIMARES", "GUIMARAS", "GUIMARAE"],
    "MOURA": ["MOURA", "OURA", "MURA", "MORA", "MOUA", "MOUR"],
    "CORRÊA": ["CORREA", "ORREA", "CRREA", "COREA", "CORRA", "CORRE"],
    "LUÍS": ["LUIS", "UIS", "LIS", "LUS", "LUI"],
    "LUÍZA": ["LUIZA", "UIZA", "LIZA", "LUZA", "LUIA", "LUIZ"],
    "CECÍLIA": ["CECILIA", "ECILIA", "CCILIA", "CEILIA", "CECLIA", "CECIIA", "CECILA", "CECILI"],
    "ESTÊVÃO": ["ESTEVAO", "STEVAO", "ETEVAO", "ESEVAO", "ESTVAO", "ESTEAO", "ESTEVO", "ESTEVA"],
    "RAÚL": ["RAUL", "AUL", "RUL", "RAL", "RAU"],
    "JÉSSICA": ["JESSICA", "ESSICA", "JSSICA", "JESICA", "JESSCA", "JESSIA", "JESSIC"],
    "LÍVIA": ["LIVIA", "IVIA", "LVIA", "LIIA", "LIVA", "LIVI"],
    "MÁRCIO": ["MARCIO", "ARCIO", "MRCIO", "MACIO", "MARIO", "MARCO", "MARCI"],
    "MÔNICA": ["MONICA", "ONICA", "MNICA", "MOICA", "MONCA", "MONIA", "MONIC"],
    "ANDRÉ": ["ANDRE", "NDRE", "ADRE", "ANRE", "ANDE", "ANDR"],
    "CÉLIA": ["CELIA", "ELIA", "CLIA", "CEIA", "CELA", "CELI"],
    "FLÁVIA": ["FLAVIA", "LAVIA", "FAVIA", "FLVIA", "FLAIA", "FLAVA", "FLAVI"],
    "INÁCIO": ["INACIO", "NACIO", "IACIO", "INCIO", "INAIO", "INACO", "INACI"],
    "LÚCIA": ["LUCIA", "UCIA", "LCIA", "LUIA", "LUCA", "LUCI"],
    "SÔNIA": ["SONIA", "ONIA", "SNIA", "SOIA", "SONA", "SONI"],
    "TARCÍSIO": ["TARCISIO", "ARCISIO", "TRCISIO", "TACISIO", "TARISIO", "TARCSIO", "TARCIIO", "TARCISO", "TARCISI"],
    "VALÉRIA": ["VALERIA", "ALERIA", "VLERIA", "VAERIA", "VALRIA", "VALEIA", "VALERA", "VALERI"],
    "WÁGNER": ["WAGNER", "AGNER", "WGNER", "WANER", "WAGER", "WAGNR", "WAGNE"],
    "ÂNGELA": ["ANGELA", "NGELA", "AGELA", "ANELA", "ANGLA", "ANGEA", "ANGEL"],
    "CONCEIÇÃO": ["CONCEICAO", "ONCEICAO", "CNCEICAO", "COCEICAO", "CONEICAO", "CONCICAO", "CONCECAO", "CONCEIAO", "CONCEICO", "CONCEICA"],
    "ASSUNÇÃO": ["ASSUNCAO", "SSUNCAO", "ASUNCAO", "ASSNCAO", "ASSUCAO", "ASSUNAO", "ASSUNCO", "ASSUNCA"],
    "MÁRIO": ["MARIO", "ARIO", "MRIO", "MAIO", "MARO", "MARI"],
    "SÉRGIO": ["SERGIO", "ERGIO", "SRGIO", "SEGIO", "SERIO", "SERGO", "SERGI"],
    "CLÁUDIA": ["CLAUDIA", "LAUDIA", "CAUDIA", "CLUDIA", "CLADIA", "CLAUIA", "CLAUDA", "CLAUDI"],
    "DÉBORA": ["DEBORA", "EBORA", "DBORA", "DEORA", "DEBRA", "DEBOA", "DEBOR"],
    "GLÁUCIA": ["GLAUCIA", "LAUCIA", "GAUCIA", "GLUCIA", "GLACIA", "GLAUIA", "GLAUCA", "GLAUCI"],
    "HÉLIO": ["HELIO", "ELIO", "HLIO", "HEIO", "HELO", "HELI"],
    "ÍTALO": ["ITALO", "TALO", "IALO", "ITLO", "ITAO", "ITAL"],
    "LÉO": ["LEO"],
    "MÁRCIA": ["MARCIA", "ARCIA", "MRCIA", "MACIA", "MARIA", "MARCA", "MARCI"],
    "NÍVEA": ["NIVEA", "IVEA", "NVEA", "NIEA", "NIVA", "NIVE"],
    "OTÁVIO": ["OTAVIO", "TAVIO", "OAVIO", "OTVIO", "OTAIO", "OTAVO", "OTAVI"],
    "RÉGIS": ["REGIS", "EGIS", "RGIS", "REIS", "REGS", "REGI"],
    "SÍLVIA": ["SILVIA", "ILVIA", "SLVIA", "SIVIA", "SILIA", "SILVA", "SILVI"],
    "THALÍA": ["THALIA", "HALIA", "TALIA", "THLIA", "THAIA", "THALA", "THALI"],
    "ÚRSULA": ["URSULA", "RSULA", "USULA", "URULA", "URSLA", "URSUA", "URSUL"],
    "VIVIÁN": ["VIVIAN", "IVIAN", "VVIAN", "VIIAN", "VIVAN", "VIVIN", "VIVIA"],
    "YASMÍN": ["YASMIN", "ASMIN", "YSMIN", "YAMIN", "YASIN", "YASMN", "YASMI"],
    "ZÉ": ["ZE"],
    "ADRIÁNO": ["ADRIANO", "DRIANO", "ARIANO", "ADIANO", "ADRANO", "ADRINO", "ADRIAO", "ADRIAN"],
    "ÁLVARO": ["ALVARO", "LVARO", "AVARO", "ALARO", "ALVRO", "ALVAO", "ALVAR"],
    "BÁRBARA": ["BARBARA", "ARBARA", "BRBARA", "BABARA", "BARARA", "BARBRA", "BARBAA", "BARBAR"],
    "CÁSSIO": ["CASSIO", "ASSIO", "CSSIO", "CASIO", "CASSO", "CASSI"],
    "DÁRIO": ["DARIO", "ARIO", "DRIO", "DAIO", "DARO", "DARI"],
    "ÉRICA": ["ERICA", "RICA", "EICA", "ERCA", "ERIA", "ERIC"],
    "FÁBIO": ["FABIO", "ABIO", "FBIO", "FAIO", "FABO", "FABI"],
    "GÉSSICA": ["GESSICA", "ESSICA", "GSSICA", "GESICA", "GESSCA", "GESSIA", "GESSIC"],
    "ÍRIS": ["IRIS", "RIS", "IIS", "IRS", "IRI"],
    "JOÁS": ["JOAS", "OAS", "JAS", "JOS", "JOA"],
    "KÁTIA": ["KATIA", "ATIA", "KTIA", "KAIA", "KATA", "KATI"],
    "LAÉRCIO": ["LAERCIO", "AERCIO", "LERCIO", "LARCIO", "LAECIO", "LAERIO", "LAERCO", "LAERCI"],
    "MAGNÓLIA": ["MAGNOLIA", "AGNOLIA", "MGNOLIA", "MANOLIA", "MAGOLIA", "MAGNLIA", "MAGNOIA", "MAGNOLA", "MAGNOLI"],
    "NÁDIA": ["NADIA", "ADIA", "NDIA", "NAIA", "NADA", "NADI"],
    "OLÍVIA": ["OLIVIA", "LIVIA", "OIVIA", "OLVIA", "OLIIA", "OLIVA", "OLIVI"],
    "QUITÉRIA": ["QUITERIA", "UITERIA", "QITERIA", "QUTERIA", "QUIERIA", "QUITRIA", "QUITEIA", "QUITERA", "QUITERI"],
    "ROMÁRIO": ["ROMARIO", "OMARIO", "RMARIO", "ROARIO", "ROMRIO", "ROMAIO", "ROMARO", "ROMARI"],
    "TÁRCIO": ["TARCIO", "ARCIO", "TRCIO", "TACIO", "TARIO", "TARCO", "TARCI"],
    "UBIRATÃ": ["UBIRATA", "BIRATA", "UIRATA", "UBRATA", "UBIATA", "UBIRTA", "UBIRAA", "UBIRAT"],
    "VITÓRIO": ["VITORIO", "ITORIO", "VTORIO", "VIORIO", "VITRIO", "VITOIO", "VITORO", "VITORI"],
    "WALQUÍRIA": ["WALQUIRIA", "ALQUIRIA", "WLQUIRIA", "WAQUIRIA", "WALUIRIA", "WALQIRIA", "WALQURIA", "WALQUIIA", "WALQUIRA", "WALQUIRI"],
    "YURÍ": ["YURI", "URI", "YRI", "YUI", "YUR"],
    "ZULMÍRA": ["ZULMIRA", "ULMIRA", "ZLMIRA", "ZUMIRA", "ZULIRA", "ZULMRA", "ZULMIA", "ZULMIR"],
    "ABRAÃO": ["ABRAAO", "BRAAO", "ARAAO", "ABAAO", "ABRAO", "ABRAA"],
    "ADRIÃO": ["ADRIAO", "DRIAO", "ARIAO", "ADIAO", "ADRAO", "ADRIO", "ADRIA"],
    "ASCENSÃO": ["ASCENSAO", "SCENSAO", "ACENSAO", "ASENSAO", "ASCNSAO", "ASCESAO", "ASCENAO", "ASCENSO", "ASCENSA"],
    "ÁUREA": ["AUREA", "UREA", "AREA", "AUEA", "AURA", "AURE"],
    "BONIFÁCIO": ["BONIFACIO", "ONIFACIO", "BNIFACIO", "BOIFACIO", "BONFACIO", "BONIACIO", "BONIFCIO", "BONIFAIO", "BONIFACO", "BONIFACI"],
    "BRÁULIO": ["BRAULIO", "RAULIO", "BAULIO", "BRULIO", "BRALIO", "BRAUIO", "BRAULO", "BRAULI"],
    "CÂNDIDO": ["CANDIDO", "ANDIDO", "CNDIDO", "CADIDO", "CANIDO", "CANDDO", "CANDIO", "CANDID"],
    "CESÁRIO": ["CESARIO", "ESARIO", "CSARIO", "CEARIO", "CESRIO", "CESAIO", "CESARO", "CESARI"],
    "CRISTÓVÃO": ["CRISTOVAO", "RISTOVAO", "CISTOVAO", "CRSTOVAO", "CRITOVAO", "CRISOVAO", "CRISTVAO", "CRISTOAO", "CRISTOVO", "CRISTOVA"],
    "CUSTÓDIO": ["CUSTODIO", "USTODIO", "CSTODIO", "CUTODIO", "CUSODIO", "CUSTDIO", "CUSTOIO", "CUSTODO", "CUSTODI"],
    "DARCÍ": ["DARCI", "ARCI", "DRCI", "DACI", "DARI", "DARC"],
    "DÉCIO": ["DECIO", "ECIO", "DCIO", "DEIO", "DECO", "DECI"],
    "DEMÉTRIO": ["DEMETRIO", "EMETRIO", "DMETRIO", "DEETRIO", "DEMTRIO", "DEMERIO", "DEMETIO", "DEMETRO", "DEMETRI"],
    "DESIDÉRIO": ["DESIDERIO", "ESIDERIO", "DSIDERIO", "DEIDERIO", "DESDERIO", "DESIERIO", "DESIDRIO", "DESIDEIO", "DESIDERO", "DESIDERI"],
    "DIONÍSIO": ["DIONISIO", "IONISIO", "DONISIO", "DINISIO", "DIOISIO", "DIONSIO", "DIONIIO", "DIONISO", "DIONISI"],
    "EDÍLSON": ["EDILSON", "DILSON", "EILSON", "EDLSON", "EDISON", "EDILON", "EDILSN", "EDILSO"],
    "EFIGÊNIA": ["EFIGENIA", "FIGENIA", "EIGENIA", "EFGENIA", "EFIENIA", "EFIGNIA", "EFIGEIA", "EFIGENA", "EFIGENI"],
    "EMÍLIA": ["EMILIA", "MILIA", "EILIA", "EMLIA", "EMIIA", "EMILA", "EMILI"],
    "ENÉAS": ["ENEAS", "NEAS", "EEAS", "ENAS", "ENES", "ENEA"],
    "EUGÊNIO": ["EUGENIO", "UGENIO", "EGENIO", "EUENIO", "EUGNIO", "EUGEIO", "EUGENO", "EUGENI"],
    "EULÁLIA": ["EULALIA", "ULALIA", "ELALIA", "EUALIA", "EULLIA", "EULAIA", "EULALA", "EULALI"],
    "EUSTÁQUIO": ["EUSTAQUIO", "USTAQUIO", "ESTAQUIO", "EUTAQUIO", "EUSAQUIO", "EUSTQUIO", "EUSTAUIO", "EUSTAQIO", "EUSTAQUO", "EUSTAQUI"],
    "FELÍCIO": ["FELICIO", "ELICIO", "FLICIO", "FEICIO", "FELCIO", "FELIIO", "FELICO", "FELICI"],
    "GENÉSIO": ["GENESIO", "ENESIO", "GNESIO", "GEESIO", "GENSIO", "GENEIO", "GENESO", "GENESI"],
    "GETÚLIO": ["GETULIO", "ETULIO", "GTULIO", "GEULIO", "GETLIO", "GETUIO", "GETULO", "GETULI"],
    "GREGÓRIO": ["GREGORIO", "REGORIO", "GEGORIO", "GRGORIO", "GREORIO", "GREGRIO", "GREGOIO", "GREGORO", "GREGORI"],
    "HELOÍSA": ["HELOISA", "ELOISA", "HLOISA", "HEOISA", "HELISA", "HELOSA", "HELOIA", "HELOIS"],
    "HILÁRIO": ["HILARIO", "ILARIO", "HLARIO", "HIARIO", "HILRIO", "HILAIO", "HILARO", "HILARI"],
    "HIPÓLITO": ["HIPOLITO", "IPOLITO", "HPOLITO", "HIOLITO", "HIPLITO", "HIPOITO", "HIPOLTO", "HIPOLIO", "HIPOLIT"],
    "HONÓRIO": ["HONORIO", "ONORIO", "HNORIO", "HOORIO", "HONRIO", "HONOIO", "HONORO", "HONORI"],
    "HORÁCIO": ["HORACIO", "ORACIO", "HRACIO", "HOACIO", "HORCIO", "HORAIO", "HORACO", "HORACI"],
    "HORTÊNCIA": ["HORTENCIA", "ORTENCIA", "HRTENCIA", "HOTENCIA", "HORENCIA", "HORTNCIA", "HORTECIA", "HORTENIA", "HORTENCA", "HORTENCI"],
    "ISAÍAS": ["ISAIAS", "SAIAS", "IAIAS", "ISIAS", "ISAAS", "ISAIS", "ISAIA"],
    "JANAÍNA": ["JANAINA", "ANAINA", "JNAINA", "JAAINA", "JANINA", "JANANA", "JANAIA", "JANAIN"],
    "JANUÁRIO": ["JANUARIO", "ANUARIO", "JNUARIO", "JAUARIO", "JANARIO", "JANURIO", "JANUAIO", "JANUARO", "JANUARI"],
    "JERÔNIMO": ["JERONIMO", "ERONIMO", "JRONIMO", "JEONIMO", "JERNIMO", "JEROIMO", "JERONMO", "JERONIO", "JERONIM"],
    "JESUÍNO": ["JESUINO", "ESUINO", "JSUINO", "JEUINO", "JESINO", "JESUNO", "JESUIO", "JESUIN"],
    "JORDÃO": ["JORDAO", "ORDAO", "JRDAO", "JODAO", "JORAO", "JORDO", "JORDA"],
    "JOSAFÁ": ["JOSAFA", "OSAFA", "JSAFA", "JOAFA", "JOSFA", "JOSAA", "JOSAF"],
    "JOSUÉ": ["JOSUE", "OSUE", "JSUE", "JOUE", "JOSE", "JOSU"],
    "LÁZARO": ["LAZARO", "AZARO", "LZARO", "LAARO", "LAZRO", "LAZAO", "LAZAR"],
    "LÍDIA": ["LIDIA", "IDIA", "LDIA", "LIIA", "LIDA", "LIDI"],
    "LÍGIA": ["LIGIA", "IGIA", "LGIA", "LIIA", "LIGA", "LIGI"],
    "LÚCIO": ["LUCIO", "UCIO", "LCIO", "LUIO", "LUCO", "LUCI"],
    "MAGALHÃES": ["MAGALHAES", "AGALHAES", "MGALHAES", "MAALHAES", "MAGLHAES", "MAGAHAES", "MAGALAES", "MAGALHES", "MAGALHAS", "MAGALHAE"],
    "MOISÉS": ["MOISES", "OISES", "MISES", "MOSES", "MOIES", "MOISS", "MOISE"],
    "NAZARÉ": ["NAZARE", "AZARE", "NZARE", "NAARE", "NAZRE", "NAZAE", "NAZAR"],
    "NOÊMIA": ["NOEMIA", "OEMIA", "NEMIA", "NOMIA", "NOEIA", "NOEMA", "NOEMI"],
    "OLÍMPIO": ["OLIMPIO", "LIMPIO", "OIMPIO", "OLMPIO", "OLIPIO", "OLIMIO", "OLIMPO", "OLIMPI"],
    "PERPÉTUA": ["PERPETUA", "ERPETUA", "PRPETUA", "PEPETUA", "PERETUA", "PERPTUA", "PERPEUA", "PERPETA", "PERPETU"],
    "PLÁCIDO": ["PLACIDO", "LACIDO", "PACIDO", "PLCIDO", "PLAIDO", "PLACDO", "PLACIO", "PLACID"],
    "SALOMÃO": ["SALOMAO", "ALOMAO", "SLOMAO", "SAOMAO", "SALMAO", "SALOAO", "SALOMO", "SALOMA"],
    "SEBASTIÃO": ["SEBASTIAO", "EBASTIAO", "SBASTIAO", "SEASTIAO", "SEBSTIAO", "SEBATIAO", "SEBASIAO", "SEBASTAO", "SEBASTIO", "SEBASTIA"],
    "SIMÃO": ["SIMAO", "IMAO", "SMAO", "SIAO", "SIMO", "SIMA"],
    "TAÍS": ["TAIS", "AIS", "TIS", "TAS", "TAI"],
    "TEÓFILO": ["TEOFILO", "EOFILO", "TOFILO", "TEFILO", "TEOILO", "TEOFLO", "TEOFIO", "TEOFIL"],
    "TOMÁS": ["TOMAS", "OMAS", "TMAS", "TOAS", "TOMS", "TOMA"],
    "ZOÉ": ["ZOE"]
}

_plate_re_1 = re.compile(r"^[A-Z]{3}\d{4}$", re.IGNORECASE)
_plate_re_2 = re.compile(r"^[A-Z0-9]{5,8}$", re.IGNORECASE)

_token_re = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9\-]+")

def tokens(text: str) -> List[str]:
    return _token_re.findall(str(text or ""))

def _is_plate(tok: str) -> bool:
    t = tok.strip().upper()
    if _plate_re_1.match(t):
        return True
    # second pattern: alnum 5-8 with at least one digit
    if _plate_re_2.match(t) and re.search(r"\d", t):
        return True
    return False

def detectar_status(texto: str) -> Tuple[str, str]:
    """
    Retorna (STATUS, texto_sem_status)
    STATUS é uma string padronizada ('MORADOR','VISITANTE','PRESTADOR','DESCONHECIDO')
    """
    if not texto:
        return "DESCONHECIDO", texto or ""
    toks = [t.upper() for t in tokens(texto)]
    found = None
    for t in toks:
        if t in _STATUS_WORDS:
            # map to canonical
            for k, aliases in _STATUS_MAP.items():
                if t in [a.upper() for a in aliases]:
                    found = k
                    break
            if found:
                break
    if not found:
        found = "DESCONHECIDO"
    # remove status words from text (first occurrences)
    pattern = r"\b(" + "|".join(re.escape(w) for w in _STATUS_WORDS) + r")\b"
    cleaned = re.sub(pattern, "", texto, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return found, cleaned

def remover_status(texto: str) -> str:
    st, cleaned = detectar_status(texto)
    return cleaned

# ===== utilities to normalize/match model candidates =====

def _normalize_token(tok: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(tok or "").upper())

def _edit_distance(a: str, b: str) -> int:
    # classic Levenshtein (efficient enough for short tokens)
    a = a or ""
    b = b or ""
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1): dp[i][0] = i
    for j in range(lb + 1): dp[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[la][lb]

def _map_to_canonical_model(candidate: str) -> str:
    """Tenta mapear um candidato de modelo a uma chave canônica em VEICULOS_MAP.
    Estratégia:
      - busca igualdade com chave ou abreviações
      - busca igualdade normalizada
      - se não houver, tenta correspondência por distância de edição <=1 com chaves/abrev
      - se nada, retorna candidate.upper()
    """
    if not candidate:
        return ""
    cand_norm = _normalize_token(candidate)
    # exact matches
    for key, abrevs in VEICULOS_MAP.items():
        if cand_norm == _normalize_token(key):
            return key.upper()
        for a in abrevs:
            if cand_norm == _normalize_token(a):
                return key.upper()
    # substring / startswith (helps JETA -> JETTA)
    for key, abrevs in VEICULOS_MAP.items():
        kn = _normalize_token(key)
        if cand_norm in kn or kn in cand_norm:
            return key.upper()
    # edit distance <=1
    cand_short = cand_norm
    best_key = None
    best_dist = None
    for key, abrevs in VEICULOS_MAP.items():
        kn = _normalize_token(key)
        d = _edit_distance(cand_short, kn)
        if best_dist is None or d < best_dist:
            best_dist = d; best_key = key
        for a in abrevs:
            an = _normalize_token(a)
            d2 = _edit_distance(cand_short, an)
            if best_dist is None or d2 < best_dist:
                best_dist = d2; best_key = key
    if best_dist is not None and best_dist <= 1:
        return best_key.upper()
    return candidate.upper()

# ---------- model/color/block/ap helpers already used by original code ----------

def _find_model_candidates(toks_up: List[str]) -> List[str]:
    found = []
    # direct detection via VEICULOS_MAP keys/abrev
    for i, tok in enumerate(toks_up):
        for modelo_key, abrevs in VEICULOS_MAP.items():
            if tok.upper() == modelo_key.upper() or tok.upper() in [a.upper() for a in abrevs]:
                found.append(modelo_key.upper())
    # also try to look near plate: if token previous to plate is alphabetic and length>2, treat as model
    for i, tok in enumerate(toks_up):
        if _is_plate(tok):
            if i-1 >= 0:
                cand = toks_up[i-1]
                if cand.isalpha() and len(cand) >= 2 and cand.upper() not in _CORES_SET and cand.upper() not in _STATUS_WORDS:
                    found.append(cand.upper().title())
            # also check next tokens
            if i+1 < len(toks_up):
                cand2 = toks_up[i+1]
                if cand2.isalpha() and len(cand2) >= 2 and cand2.upper() not in _CORES_SET and cand2.upper() not in _STATUS_WORDS:
                    found.append(cand2.upper().title())
    # dedupe preserving order
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return out

def _find_color_candidates(toks_up: List[str]) -> List[str]:
    out = []
    for t in toks_up:
        if t.upper() in _CORES_SET:
            out.append(t.upper())
    return out

def _find_block_ap(toks_up: List[str]) -> (str, str):
    bloco = ""
    apt = ""
    for i, t in enumerate(toks_up):
        # BL10, BL-10 patterns
        m = re.match(r"^BL(?:OCO)?[-:]?(\d+)$", t, flags=re.IGNORECASE)
        if m:
            bloco = m.group(1)
            continue
        if t.startswith("BL") and t[2:].isdigit():
            bloco = t[2:]
            continue
        if t == "BLOCO":
            if i+1 < len(toks_up) and toks_up[i+1].isdigit():
                bloco = toks_up[i+1]
        if t in ("AP","APT","APTO","APARTAMENTO"):
            if i+1 < len(toks_up) and toks_up[i+1].isdigit():
                apt = toks_up[i+1]
                continue
        m2 = re.match(r"^AP(?:T|ARTAMENTO)?[-:]?(\d+)$", t, flags=re.IGNORECASE)
        if m2:
            apt = m2.group(1)
            continue
        if t.startswith("AP") and t[2:].isdigit():
            apt = t[2:]
            continue
    return bloco or "", apt or ""

def _extract_plate_and_indices(toks: List[str]) -> (str, int):
    # return (plate, index) of first found plate, else ("", -1)
    for i, t in enumerate(toks):
        if _is_plate(t):
            return t.upper(), i
    return "", -1

# =========================
# função principal: extrair_tudo_consumo
# =========================

def extrair_tudo_consumo(texto: str) -> Dict[str, Any]:
    """
    Extrai de forma robusta:
    - PLACA
    - MODELOS (lista)
    - COR
    - BLOCO, APARTAMENTO
    - NOME_RAW (possível nome completo)
    - STATUS
    - TEXTO_LIMPO (texto sem status)
    Retorna dicionário com keys (uppercase):
      { "TEXTO_LIMPO","COR","PLACA","BLOCO","APARTAMENTO","MODELOS","NOME_RAW","STATUS" }
    """
    original = (texto or "").strip()
    toks = tokens(original)
    toks_up = [t.upper() for t in toks]

    status, texto_sem_status = detectar_status(original)
    # recompute tokens without status words for some heuristics
    toks_ns = tokens(texto_sem_status)
    toks_ns_up = [t.upper() for t in toks_ns]

    placa, plate_idx = _extract_plate_and_indices(toks_up)

    bloco, apt = _find_block_ap(toks_up)

    modelos = _find_model_candidates(toks_up)
    # normalize/map modelos to canonical keys when possible and record their token indices to exclude from name
    modelos_mapped = []
    modelo_indices = set()
    if modelos:
        # modelos may be strings (from map keys) or heuristics (like 'JETA')
        for cand in modelos:
            canon = _map_to_canonical_model(str(cand))
            if canon and canon not in modelos_mapped:
                modelos_mapped.append(canon)
    else:
        modelos_mapped = []

    # ALSO, try to find model candidates near plate (again) and map them
    if plate_idx >= 0:
        # check previous token
        if plate_idx - 1 >= 0:
            p = toks_up[plate_idx - 1]
            if p.isalpha() and p.upper() not in _CORES_SET and p.upper() not in _STATUS_WORDS:
                cand = _map_to_canonical_model(p)
                if cand and cand not in modelos_mapped:
                    modelos_mapped.insert(0, cand)
            # se o token anterior é cor, tente o anterior a ele (ex: JETA PRETO FEU3C84)
            if p.upper() in _CORES_SET and plate_idx - 2 >= 0:
                p_prev = toks_up[plate_idx - 2]
                if p_prev.isalpha() and p_prev.upper() not in _STATUS_WORDS:
                    cand = _map_to_canonical_model(p_prev)
                    if cand and cand not in modelos_mapped:
                        modelos_mapped.insert(0, cand)
        # check next token
        if plate_idx + 1 < len(toks_up):
            p2 = toks_up[plate_idx + 1]
            if p2.isalpha() and p2.upper() not in _CORES_SET and p2.upper() not in _STATUS_WORDS:
                cand = _map_to_canonical_model(p2)
                if cand and cand not in modelos_mapped:
                    modelos_mapped.append(cand)
            # se o token seguinte é cor, tente o próximo a ele
            if p2.upper() in _CORES_SET and plate_idx + 2 < len(toks_up):
                p_next = toks_up[plate_idx + 2]
                if p_next.isalpha() and p_next.upper() not in _STATUS_WORDS:
                    cand = _map_to_canonical_model(p_next)
                    if cand and cand not in modelos_mapped:
                        modelos_mapped.append(cand)

    # dedupe modelos_mapped preserve order
    modelos_final = []
    for m in modelos_mapped:
        if m and m not in modelos_final:
            modelos_final.append(m)

    # find indices of tokens that correspond to model candidates (either exact match or normalized match)
    for i, t in enumerate(toks_up):
        tn = _normalize_token(t)
        for m in modelos_final:
            if tn == _normalize_token(m) or tn == _normalize_token(m[:4]) or m.upper().startswith(tn) or tn.startswith(_normalize_token(m)):
                modelo_indices.add(i)

    cores = _find_color_candidates(toks_up)
    cor = cores[0] if cores else ""

    # Name extraction: choose tokens that are alphabetic and not identified as other fields
    marked_indices = set()
    # mark plate index
    if plate_idx >= 0:
        marked_indices.add(plate_idx)
    # mark block/ap tokens indices
    for i,t in enumerate(toks_up):
        if re.match(r"^BL(?:OCO)?[-:]?\d+$", t) or (t.startswith("BL") and t[2:].isdigit()) or t=="BLOCO":
            marked_indices.add(i)
        if re.match(r"^AP(?:T|ARTAMENTO)?[-:]?\d+$", t) or (t.startswith("AP") and t[2:].isdigit()) or t in ("AP","APT","APTO","APARTAMENTO"):
            marked_indices.add(i)
    # mark status word indices and color/model tokens
    for i,t in enumerate(toks_up):
        if t in _STATUS_WORDS:
            marked_indices.add(i)
        if t in _CORES_SET:
            marked_indices.add(i)
        for modelo_key, abrevs in VEICULOS_MAP.items():
            if t == modelo_key.upper() or t in [a.upper() for a in abrevs]:
                marked_indices.add(i)
    # mark heuristic-detected model indices as well
    marked_indices.update(modelo_indices)

    # candidate name tokens (alphabetic, not marked)
    candidate_name_tokens = []
    for i,t in enumerate(toks_up):
        if i in marked_indices: continue
        # token should contain alphabetic characters
        if re.search(r"[A-ZÀ-ÖØ-öø-ÿ]", t) and not re.search(r"\d", t):
            candidate_name_tokens.append((i, t))

    # Build name_raw: choose contiguous sequence of up to 3 candidate tokens with likely person name
    name_raw = ""
    if candidate_name_tokens:
        seq = [t for i,t in candidate_name_tokens]
        # filter out common prepositions/particles
        stopwords = set(["DO","DA","DE","DOS","DAS","E","O","A","SR","SRA"])
        cleaned_seq = [t for t in seq if t.upper() not in stopwords]
        if cleaned_seq:
            top = cleaned_seq[:3]
            name_raw = " ".join([x.title() for x in top])
        else:
            name_raw = seq[0].title()
    else:
        name_raw = ""

    # Fallback: if there's a 'name-looking' block before block/ap token, use that
    if not name_raw:
        first_struct_idx = None
        for i,t in enumerate(toks_up):
            if i in marked_indices:
                first_struct_idx = i
                break
        if first_struct_idx:
            cand = [toks[j] for j in range(0, first_struct_idx) if toks[j].isalpha()]
            if cand:
                name_raw = " ".join([c.title() for c in cand[:3]])

    # TEXTO_LIMPO: original minus status word(s)
    texto_limpo = texto_sem_status.strip()
    if texto_limpo == "":
        texto_limpo = original

    return {
        "TEXTO_LIMPO": texto_limpo,
        "COR": cor.upper() if cor else "",
        "PLACA": placa.upper() if placa else "",
        "BLOCO": bloco,
        "APARTAMENTO": apt,
        "MODELOS": [m.upper() for m in modelos_final] if modelos_final else [],
        "NOME_RAW": name_raw.upper() if name_raw else "",
        "STATUS": status.upper() if status else "DESCONHECIDO"
    }