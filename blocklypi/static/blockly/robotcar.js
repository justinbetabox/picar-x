Blockly.Blocks['forward'] = {
    init: function() {
      this.appendDummyInput()
          .appendField("forward");
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(230);
   this.setTooltip("");
   this.setHelpUrl("");
    }
  };

  Blockly.Python['forward'] = function(block) {
    // TODO: Assemble Python into code variable.
    var code = 'px.forward()\n';
    return code;
  };