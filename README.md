# Ember

Ember is a GUI platform designed to iteratively bring applied research in program analysis to the field and incorporate users in the research cycle.

Ember _is not_ a replacement for existing interactive disassemblers with a GUI, instead it is meant to complement existing tools such as Ghidra and IDA Pro. Ember is designed to work with any interactive disassembler using plugins and RPC calls that coordinate UI events between the disassembler and Ember.

Ghidra support is being worked on now and support for other disassemblers will be added as needed.

## Features (*Planned)
  * A library of base views that can be extended to provide customized GUIs
  * An extension architecture that allows researchers and developers to package their tools for use in Ember*
  * Inter-extension coordination that allows extensions to provide APIs for integration with Ember, other extensions, and interactive disassemblers*
  * Interactive Python console that allows for real-time modification of the Ember environment*
  * UI and analysis event system to keep Ember extensions and external tools synchronized*

Distribution A. (Approved for public release; distribution unlimited.)
