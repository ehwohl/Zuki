class PitchProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
  }

  process(inputs) {
    const channel = inputs[0]?.[0]
    if (channel && channel.length > 0) {
      this.port.postMessage(channel.slice())
    }
    return true
  }
}

registerProcessor('pitch-processor', PitchProcessor)
