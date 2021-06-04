<template>
  <v-hover v-slot:default="{ hover }">
    <v-card
      class="flowchart-node"
      :style="nodeStyle"
      @mousedown="handleMousedown"
      v-bind:class="{ selected: options.selected === id }"
      rounded
      :loading="loading"
    >
      <!-- Input Port -->
      <FlowchartNodePort
        v-if="!container_is_input"
        class="node-port node-input"
        @mouseup="$emit('linkingStop')"
      />

      <!-- Node Data -->
      <v-card-title style="word-break: break-word">
        {{ type }}
        <v-chip-group column class="mt-3">
          <v-chip
            v-for="(tag, index) in tags"
            :key="`tag${index}`"
            v-text="tag.tag_name"
            class="mr-1 mb-1"
            color="primary"
            x-small
            outlined
          />
        </v-chip-group>
        <v-icon-btn
          v-if="selected && selected.host !== '*' && container_is_input"
          :icon="echoIcon"
          @click="sendEcho(selected)"
        />
      </v-card-title>
      <v-select
        v-if="container_is_output || container_is_input"
        v-model="selected"
        :items="destinations"
        item-text="title"
        item-value="id"
        label="Application Entity"
        dense
        solo
        flat
        return-object
        single-line
        @change="changeDestination(selected)"
      >
        <template v-slot:prepend-item>
          <v-list-item>
            <v-list-item-content>
              <v-list-item-title>
                Add A Destination
              </v-list-item-title>
            </v-list-item-content>
            <v-list-item-action>
              <v-icon-btn add @click="$emit('showDestinationForm')" />
            </v-list-item-action>
          </v-list-item>
          <v-divider light />
        </template>
      </v-select>
      <v-expand-transition>
        <v-toolbar
          v-if="hover"
          style="position: absolute; bottom: 0; width: inherit"
          flat
          color="primary"
          dense
          class="pa-0"
        >
          <v-btn
            text
            color="accent"
            v-if="container_is_input"
            @click="$emit('showConditionBuilder')"
          >
            Rules
          </v-btn>
          <v-spacer />
          <v-icon-btn
            v-if="canEdit"
            delete
            color="accent"
            @click="$emit('deleteNode')"
          />
        </v-toolbar>
      </v-expand-transition>

      <!-- Output Port -->
      <FlowchartNodePort
        v-if="!container_is_output"
        class="node-port node-output"
        @mousedown="$emit('linkingStart')"
      />
    </v-card>
  </v-hover>
</template>

<script>
import echoMixin from '@/utilities/echoMixin'
import FlowchartNodePort from './FlowchartNodePort.vue'
import OutputDestinationForm from './OutputDestinationForm'
import { mapState } from 'vuex'

export default {
  name: 'FlowchartNode',
  components: { FlowchartNodePort, OutputDestinationForm },
  mixins: [echoMixin],
  props: {
    canEdit: { type: Boolean },
    id: { type: Number },
    y: { type: Number },
    x: { type: Number },
    type: { type: String },
    tags: { type: Array },
    container_is_input: { type: Boolean },
    container_is_output: { type: Boolean },
    destination: { type: Object },
    options: {
      type: Object,
      default() {
        return {
          centerX: undefined,
          scale: undefined,
          centerY: undefined
        }
      }
    },
    scene: {
      type: Object,
      default: () => ({
        centerX: 1024,
        scale: 1,
        centerY: 140,
        nodes: [],
        links: []
      })
    },
    colors: {
      type: Object,
      default: () => ({
        input: 'orange',
        output: 'purple',
        default: 'blue'
      })
    }
  },
  data: () => ({
    destinationDialog: false,
    show: {
      delete: false
    },
    selected: undefined
  }),
  computed: {
    ...mapState('destination', ['destinations']),
    nodeStyle() {
      return {
        top: this.options.centerY + this.y * this.options.scale + 'px',
        left: this.options.centerX + this.x * this.options.scale + 'px',
        transform: `scale(${this.options.scale})`
      }
    },
    nodeColor: ctx => {
      if (ctx.container_is_output) return ctx.colors.output
      else if (ctx.container_is_input) return ctx.colors.input
      else return ctx.colors.default
    }
  },
  created() {
    if (this.container_is_output || this.container_is_input)
      this.$store.dispatch('destination/fetchDestinations')
    if (this.destination) this.selected = this.destination

    if (this.selected) {
      this.$emit('setDestination', {
        pipelineNodeId: this.id,
        destinationId: this.selected?.id
      })
    }
  },
  methods: {
    changeDestination() {
      this.$emit('setDestination', {
        pipelineNodeId: this.id,
        destinationId: this.selected.id
      })
    },
    handleMousedown(e) {
      // This could be removed with click.stop maybe?
      if (
        e.target.className.indexOf('node-input') < 0 &&
        e.target.className.indexOf('node-output') < 0
      ) {
        this.$emit('nodeSelected', e)
      }
      e.preventDefault()
    }
  }
}
</script>

<style scoped lang="scss">
.poll-name {
  overflow: hidden;
  text-overflow: ellipsis;
  word-wrap: break-word;
}
.flowchart-node {
  margin: 0;
  width: 200px;
  height: 170px;
  position: absolute;
  box-sizing: border-box;
  z-index: 10;
  opacity: 0.95;
  cursor: move;
  transform-origin: top left;

  .node-port {
    position: absolute;
    left: 50%;
    transform: translate(-50%);
  }

  /* TODO: Make this dynamic sized */
  .node-input {
    left: 0%;
    top: 45%;
  }

  .node-output {
    left: 100%;
    top: 45%;
  }
}
</style>
