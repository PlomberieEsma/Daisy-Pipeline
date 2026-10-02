fu = resolve.Fusion()
print("fu:", fu)
print("UIManager:", fu.UIManager if fu else None)
print("bmd:", bmd)
try:
    print("fusion:", fusion)   # variable injectée par Resolve, si elle existe
except NameError:
    print("pas de variable fusion")