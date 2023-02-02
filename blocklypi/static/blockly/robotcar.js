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

Blockly.Blocks['backward'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("backward");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};

Blockly.Python['backward'] = function(block) {
  // TODO: Assemble Python into code variable.
  var code = 'px.backward()\n';
  return code;
};

Blockly.Blocks['sleep'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("sleep")
        .appendField(new Blockly.FieldNumber(0, 0, 25), "time");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};

Blockly.Python['sleep'] = function(block) {
  var number_time = block.getFieldValue('time');
  // TODO: Assemble Python into code variable.
  var code = 'time.sleep(' + number_time + ')\n';
  return code;
};

Blockly.Blocks['stop'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("stop");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};

Blockly.Python['stop'] = function(block) {
  // TODO: Assemble Python into code variable.
  var code = 'px.stop()\n';
  return code;
};

Blockly.Blocks['turn'] = {
  init: function() {
    this.appendDummyInput()
        .appendField("turn")
        .appendField(new Blockly.FieldNumber(0, -30, 30), "angle")
        .appendField("º");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};

Blockly.Python['turn'] = function(block) {
  var number_angle = block.getFieldValue('angle');
  // TODO: Assemble Python into code variable.
  var code = 'px.set_dir_servo_angle(' + number_angle + ')\n';
  return code;
};

Blockly.Blocks['set_speed'] = {
  init: function() {
    this.appendDummyInput()
        .appendField(new Blockly.FieldLabelSerializable("Set Speed to"), "speed_label")
        .appendField(new Blockly.FieldNumber(0, 0, 100), "speed");
    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
 this.setTooltip("");
 this.setHelpUrl("");
  }
};

Blockly.Python['set_speed'] = function(block) {
  var number_speed = block.getFieldValue('speed');
  // TODO: Assemble Python into code variable.
  var code = 'px.speed = ' + number_speed + '\n';
  return code;
};