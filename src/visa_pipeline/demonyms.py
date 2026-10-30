"""Demonym to ISO 3166-1 alpha-2 passport code mapping."""

# Hand-written mapping covering all UN members plus TW, HK, MO, PS, XK
# Based on Wikipedia "Visa requirements for X citizens" page titles
DEMONYM_TO_ISO2 = {
    # A
    "Afghan": "AF",
    "Albanian": "AL",
    "Algerian": "DZ",
    "American": "US",
    "Andorran": "AD",
    "Angolan": "AO",
    "Antigua and Barbuda": "AG",
    "Antiguan and Barbudan": "AG",
    "Argentine": "AR",
    "Argentinian": "AR",
    "Armenian": "AM",
    "Australian": "AU",
    "Austrian": "AT",
    "Azerbaijani": "AZ",

    # B
    "Bahamian": "BS",
    "Bahraini": "BH",
    "Bangladeshi": "BD",
    "Barbadian": "BB",
    "Belarusian": "BY",
    "Belgian": "BE",
    "Belizean": "BZ",
    "Beninese": "BJ",
    "Bhutanese": "BT",
    "Bolivian": "BO",
    "Bosnia and Herzegovina": "BA",
    "Bosnia-Herzegovina": "BA",
    "Bosnian-Herzegovinian": "BA",
    "Botswana": "BW",
    "Motswana": "BW",
    "Brazilian": "BR",
    "Bruneian": "BN",
    "Bulgarian": "BG",
    "Burkinabé": "BF",
    "Burkinabe": "BF",
    "Burundian": "BI",
    "Bissau-Guinean": "GW",
    "British": "GB",

    # C
    "Cabo Verdean": "CV",
    "Cape Verdean": "CV",
    "Cambodian": "KH",
    "Cameroonian": "CM",
    "Canadian": "CA",
    "Central African": "CF",
    "Chadian": "TD",
    "Chilean": "CL",
    "Chinese": "CN",
    "Colombian": "CO",
    "Comorian": "KM",
    "Congolese (Democratic Republic of the Congo)": "CD",
    "Democratic Republic of the Congo": "CD",
    "Congolese (Republic of the Congo)": "CG",
    "Republic of the Congo": "CG",
    "Costa Rican": "CR",
    "Croatian": "HR",
    "Cuban": "CU",
    "Cypriot": "CY",
    "Czech": "CZ",
    "Ivorian": "CI",

    # D
    "Danish": "DK",
    "Djiboutian": "DJ",
    "Dominican": "DM",
    "Dominica": "DM",
    "Dominican Republic": "DO",

    # E
    "East Timorese": "TL",
    "Timorese": "TL",
    "Ecuadorian": "EC",
    "Egyptian": "EG",
    "Salvadoran": "SV",
    "Equatoguinean": "GQ",
    "Equatorial Guinean": "GQ",
    "Eritrean": "ER",
    "Estonian": "EE",
    "Eswatini": "SZ",
    "Swazi": "SZ",
    "Ethiopian": "ET",
    "Emirati": "AE",

    # F
    "Faroese": "FO",
    "Fijian": "FJ",
    "Finnish": "FI",
    "French": "FR",

    # G
    "Gabonese": "GA",
    "Gambian": "GM",
    "Georgian": "GE",
    "German": "DE",
    "Ghanaian": "GH",
    "Greek": "GR",
    "Greenlandic": "GL",
    "Grenadian": "GD",
    "Guatemalan": "GT",
    "Guinean": "GN",
    "Guinea-Bissauan": "GW",
    "Guyanese": "GY",

    # H
    "Haitian": "HT",
    "Honduran": "HN",
    "Hong Kong": "HK",
    "Hungarian": "HU",

    # I
    "Icelandic": "IS",
    "Indian": "IN",
    "Indonesian": "ID",
    "Iranian": "IR",
    "Iraqi": "IQ",
    "Irish": "IE",
    "Israeli": "IL",
    "Italian": "IT",

    # J
    "Jamaican": "JM",
    "Japanese": "JP",
    "Jordanian": "JO",

    # K
    "Kazakhstani": "KZ",
    "Kenyan": "KE",
    "Kiribati": "KI",
    "Kuwaiti": "KW",
    "Kyrgyzstani": "KG",
    "Kyrgyz": "KG",
    "Kosovan": "XK",
    "Kosovar": "XK",

    # L
    "Laotian": "LA",
    "Latvian": "LV",
    "Lebanese": "LB",
    "Lesotho": "LS",
    "Liberian": "LR",
    "Libyan": "LY",
    "Liechtenstein": "LI",
    "Lithuanian": "LT",
    "Luxembourgish": "LU",
    "Luxembourger": "LU",

    # M
    "Macau": "MO",
    "Macao": "MO",
    "Macedonian": "MK",
    "Malagasy": "MG",
    "Malawian": "MW",
    "Malaysian": "MY",
    "Maldivian": "MV",
    "Malian": "ML",
    "Maltese": "MT",
    "Marshall Islands": "MH",
    "Marshallese": "MH",
    "Mauritanian": "MR",
    "Mauritian": "MU",
    "Mexican": "MX",
    "Micronesian": "FM",
    "Moldovan": "MD",
    "Monaco": "MC",
    "Monegasque": "MC",
    "Monégasque": "MC",
    "Mongolian": "MN",
    "Montenegrin": "ME",
    "Moroccan": "MA",
    "Mozambican": "MZ",
    "Myanmar": "MM",
    "Burmese": "MM",

    # N
    "Namibian": "NA",
    "Nauruan": "NR",
    "Nepalese": "NP",
    "Nepali": "NP",
    "Dutch": "NL",
    "New Zealand": "NZ",
    "New Zealander": "NZ",
    "Nicaraguan": "NI",
    "Nigerien": "NE",
    "Nigerian": "NG",
    "North Korean": "KP",
    "Norwegian": "NO",

    # O
    "Omani": "OM",

    # P
    "Pakistani": "PK",
    "Palauan": "PW",
    "Palestinian": "PS",
    "Panamanian": "PA",
    "Papua New Guinean": "PG",
    "Paraguayan": "PY",
    "Peruvian": "PE",
    "Philippine": "PH",
    "Filipino": "PH",
    "Polish": "PL",
    "Portuguese": "PT",

    # Q
    "Qatari": "QA",

    # R
    "Romanian": "RO",
    "Russian": "RU",
    "Rwandan": "RW",

    # S
    "Saint Kitts and Nevis": "KN",
    "Kittitian and Nevisian": "KN",
    "Saint Lucian": "LC",
    "Saint Vincent and the Grenadines": "VC",
    "Saint Vincentian": "VC",
    "Sammarinese": "SM",
    "San Marino": "SM",
    "São Tomé and Príncipe": "ST",
    "Sao Tomean": "ST",
    "Santomean": "ST",
    "Samoan": "WS",
    "Saudi": "SA",
    "Saudi Arabian": "SA",
    "Senegalese": "SN",
    "Serbian": "RS",
    "Seychellois": "SC",
    "Seychelles": "SC",
    "Sierra Leonean": "SL",
    "Singapore": "SG",
    "Singaporean": "SG",
    "Slovak": "SK",
    "Slovene": "SI",
    "Slovenian": "SI",
    "Solomon Islands": "SB",
    "Solomon Islander": "SB",
    "Somali": "SO",
    "South African": "ZA",
    "South Korean": "KR",
    "South Sudanese": "SS",
    "Spanish": "ES",
    "Sri Lankan": "LK",
    "Sudanese": "SD",
    "Surinamese": "SR",
    "Swedish": "SE",
    "Swiss": "CH",
    "Syrian": "SY",

    # T
    "Taiwanese": "TW",
    "Tajikistani": "TJ",
    "Tanzanian": "TZ",
    "Thai": "TH",
    "Togolese": "TG",
    "Tongan": "TO",
    "Trinidadian and Tobagonian": "TT",
    "Trinidad and Tobago": "TT",
    "Tunisian": "TN",
    "Turkish": "TR",
    "Turkmen": "TM",
    "Turkmenistani": "TM",
    "Tuvaluan": "TV",

    # U
    "Ugandan": "UG",
    "Ukrainian": "UA",
    "United States": "US",
    "Uruguayan": "UY",
    "Uzbekistan": "UZ",
    "Uzbekistani": "UZ",

    # V
    "Vanuatu": "VU",
    "Vanuatuan": "VU",
    "Vatican": "VA",
    "Venezuelan": "VE",
    "Vietnamese": "VN",

    # Y
    "Yemeni": "YE",

    # Z
    "Zambian": "ZM",
    "Zimbabwean": "ZW",
}


def demonym_to_iso2(demonym: str) -> str | None:
    """
    Convert demonym to ISO 3166-1 alpha-2 code.

    Args:
        demonym: Nationality demonym (e.g., "German", "Emirati")

    Returns:
        ISO2 code or None if unmapped
    """
    return DEMONYM_TO_ISO2.get(demonym)
