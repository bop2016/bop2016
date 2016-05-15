from searchPath import searchPath

Cases = [
    ((1972106549, 1587650367), 32),
    ((2126125555, 2060367530), 5903),
    ((2107710616, 2128635872), 62110),
    ((2030985472, 2133644056), 186),
    ((2018949714, 2105005017), 595),
    ((2014261844, 57898110), 19),
    ((2126125555, 2153635508), 3592),
    ((2332023333, 57898110), 1),
    # cases above are before update, cases below are after update
    ((57898110, 2014261844), 27),
    ((2088905367, 2033660646), 115),
    ((621499171, 2100837269), 34)
]

for id_pair, expected_result in Cases:
    print(id_pair)
    print(len(searchPath(*id_pair)), expected_result)
