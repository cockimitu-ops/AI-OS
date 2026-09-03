extends SceneTree
## Der Token wanderte aus AIOSClient.gd in eine per .gitignore ausgeschlossene
## Datei, weil das Repository oeffentlich ist. Bricht dieses Laden, sendet die
## App still einen leeren Bearer und alles antwortet 401 - deshalb geprueft.
const Client = preload("res://AIOSClient.gd")

func _init() -> void:
	var token: String = Client._token()
	assert(token != "", "AIOSSecret.gd muss den Token liefern")
	assert(token.length() > 20, "Token sieht nicht nach einem echten Token aus")
	print("test_secret ok, laenge=", token.length())
	quit()
