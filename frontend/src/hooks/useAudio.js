import { ref } from 'vue'

export function useAudio() {
  const audioContext = ref(null)
  const isPlaying = ref(false)

  const initAudioContext = () => {
    if (!audioContext.value) {
      audioContext.value = new (window.AudioContext || window.webkitAudioContext)()
    }
  }

  const playSound = (soundName, options = {}) => {
    initAudioContext()
    
    const audio = new Audio()
    audio.src = `/sounds/${soundName}`
    
    const { volume = 0.5, loop = false, duration = null } = options
    
    audio.volume = volume
    audio.loop = loop
    
    audio.play().catch(error => {
      console.error(`播放音效失败: ${soundName}`, error)
    })

    isPlaying.value = true
    
    audio.addEventListener('ended', () => {
      isPlaying.value = false
    })

    if (duration) {
      setTimeout(() => {
        audio.pause()
        isPlaying.value = false
      }, duration * 1000)
    }

    return audio
  }

  const playClick = () => {
    return playSound('click.wav', { volume: 0.3 })
  }

  const playRadar = () => {
    return playSound('radar.wav', { volume: 0.4, duration: 2 })
  }

  const playWarning = () => {
    return playSound('warning.wav', { volume: 0.6, loop: true })
  }

  const stopWarning = () => {
    const allAudios = document.querySelectorAll('audio[src*="warning.wav"]')
    allAudios.forEach(audio => {
      audio.pause()
      audio.currentTime = 0
    })
    isPlaying.value = false
  }

  const stopAllSounds = () => {
    const allAudios = document.querySelectorAll('audio')
    allAudios.forEach(audio => {
      audio.pause()
      audio.currentTime = 0
    })
    isPlaying.value = false
  }

  return {
    audioContext,
    isPlaying,
    playSound,
    playClick,
    playRadar,
    playWarning,
    stopWarning,
    stopAllSounds
  }
}
