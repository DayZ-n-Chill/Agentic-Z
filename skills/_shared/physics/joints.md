# Joints

Covers the joint calls that tie two physics bodies together. Every call below is declared in `P:\scripts\1_core\proto\enphysics.c`; no vanilla gameplay script creates a joint, so there is no vanilla pattern to copy and the behavior of each limit must be confirmed in game. Both entities need a body first (`rigid-body-api.md`).

## Creating and removing

Each create call takes the two entities, the anchor data, then `bool block, float breakThreshold`, and returns a `dJoint`:

| Call | Anchor data | Line |
|---|---|---|
| `dJointCreateHinge(ent1, ent2, point1, axis1, point2, axis2, block, breakThreshold)` | A point and an axis on each body | `:212` |
| `dJointCreateHinge2`, `dJointCreateSlider`, `dJointCreateConeTwist`, `dJointCreate6DOF`, `dJointCreate6DOFSpring` | A `vector matrix[4]` frame on each body | `:213`, `:214`, `:217`, `:218`, `:219` |
| `dJointCreateBallSocket`, `dJointCreateFixed` | A point on each body | `:215`, `:216` |
| `dJointDestroy(joint)` | Removes the joint | `:220` |

A joint that breaks raises `EOnJointBreak(IEntity other, int extra)` on the entity (`P:\scripts\1_core\proto\enentity.c:207`).

## Setters per joint type

| Joint | Setters | Lines |
|---|---|---|
| Hinge | `dJointHingeSetLimits(joint, low, high, softness, biasFactor, relaxationFactor)`, `dJointHingeSetAxis`, `dJointHingeSetMotorTargetAngle(joint, angle, dt, maxImpulse)` | `:223` to `:225` |
| Cone twist | `dJointConeTwistSetAngularOnly`, `dJointConeTwistSetLimit(joint, limitIndex, value)`, `dJointConeTwistSetLimits(joint, swingSpan1, swingSpan2, twistSpan, softness, biasFactor, relaxationFactor)` | `:228`, `:240`, `:241` |
| 6DOF and 6DOF spring | `dJoint6DOFSetLinearLimits`, `dJoint6DOFSetAngularLimits`, `dJoint6DOFSetLimit(joint, axis, lo, hi)` | `:250` to `:252` |
| 6DOF spring | `dJoint6DOFSpringSetSpring(joint, axis, stiffness, damping)` | `:255` |
| Slider | Linear and angular limits, the `Dir`, `Lim` and `Ortho` softness, restitution and damping setters, `dJointSliderSetLinearMotor` and `dJointSliderSetAngularMotor(joint, velocity, force)`, and the position getters | `:258` to `:270` |

What the vanilla comments say about the values:

- Cone twist `softness` runs 0 to 1, about 0.8 to 1 recommended, and is the share of the limit where movement is free; `biasFactor` about 0.3; `relaxationFactor` near 1 (`P:\scripts\1_core\proto\enphysics.c:229-239`).
- 6DOF limits: upper below lower is free, equal is locked, upper above lower is limited; the first three axes are linear and the next three angular (`P:\scripts\1_core\proto\enphysics.c:244-249`).
- A 6DOF spring with stiffness -1 and damping -1 is switched off (`P:\scripts\1_core\proto\enphysics.c:254`).
- A slider motor with force 0 is off (`P:\scripts\1_core\proto\enphysics.c:266`).
