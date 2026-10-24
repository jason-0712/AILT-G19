"""Places transcribed from the team's supplied campus map and facilities list."""
PLACES = {
 "MW":"Meng Wah Complex", "HC":"Hui Oi Chow Science Building",
 "RM":"Runme Shaw Building", "RR":"Run Run Shaw Building",
 "JL":"James Hsioung Lee Science Building", "EH":"Eliot Hall",
 "RHT":"Rayson Huang Theatre", "CYC":"Chong Yuet Ming Chemistry Building",
 "LE":"Library Extension Building", "HW":"Haking Wong Building",
 "JCT":"The Jockey Club Tower", "CCT":"Cheng Yu Tung Building",
 "CB":"Chow Yei Ching Building", "CPD":"Central Podium Levels, Centennial Campus",
 "CRT":"Run Run Shaw Tower", "KBS":"Kadoorie Biological Sciences Building",
 "MB":"Main Building", "KB":"Knowles Building", "KK":"K.K. Leung Building",
 "TT":"T.T. Tsui Building", "CYP":"Chong Yuet Ming Physics Building",
}
for name in (
 "Chi Wah Learning Commons", "Dental Library", "Faculty of Medicine",
 "Law Library", "Main Library", "Medical Library", "Music Library",
 "Research Student Centre (Faculty of Engineering)", "Study Room at Meng Wah Complex 6/F",
 "The University of Hong Kong History Gallery", "Sun Yat-sen Place",
 "Swire Building", "Loke Yew Hall", "Simon K Y Lee Hall", "Composite Building",
 "Run Run Shaw Heritage House", "HKU MTR Station", "University Street",
 "West Gate Entrance", "Other",
):
    PLACES[name] = name
PLACE_OPTIONS = sorted(PLACES)
UNSPECIFIED = "Not recorded"

def place_words(place):
    return place + " " + PLACES.get(place, "")
